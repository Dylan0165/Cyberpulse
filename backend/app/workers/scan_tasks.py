"""Celery tasks — 8-phase scan pipeline via the Kali VM scanner API."""

import json
import logging
import time
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
import app.models  # registers all models with SQLAlchemy before any query runs
from app.models.scan import Scan
from app.models.target import Target
from app.models.scheduled_scan import ScheduledScan
from app.services.tool_runner import ToolRunner, ScannerUnavailableError
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def _runner() -> ToolRunner:
    return ToolRunner(
        host=settings.kali_vm_host,
        port=settings.kali_vm_port,
        api_key=settings.scanner_api_key,
    )


def _pub(r: sync_redis.Redis, scan_id: str, event: dict):
    """Publish a live event and also append to the replay log."""
    payload = json.dumps(event)
    r.publish(f"scan:{scan_id}:live", payload)
    r.rpush(f"scan:{scan_id}:log", payload)
    r.expire(f"scan:{scan_id}:log", 86400)


# ── Phase definitions ─────────────────────────────────────────────────────────
# Each entry: (tool_name, args_template, timeout_seconds)
# {target} and {scan_id} are substituted at runtime.
# Credential placeholders: {username}, {password}, {bearer_token}

PHASES: list[tuple[str, list[tuple[str, str, int]]]] = [
    ("recon", [
        ("nmap",     "-sV -sC --open -p- {target}",                                    480),
        # Installed as httpx-pd on Kali VM to avoid clash with Python httpx client
        ("httpx-pd", "-u http://{target} -title -tech-detect -status-code -silent",    120),
        ("whatweb",  "-a 3 {target}",                                                   60),
    ]),
    ("vuln_scan", [
        # -json deprecated in nuclei v3+; use -jsonl
        ("nuclei",   "-u {target} -severity critical,high,medium -jsonl -silent",      600),
    ]),
    ("webapp", [
        # nikto -Format json requires -output; omit Format flag to use plain text
        ("nikto",    "-h {target} -ask no",                                            300),
        ("sqlmap",   "-u {target} --batch --level=2 --risk=1 --forms",                600),
        ("ffuf",     "-u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403 -ac -t 40", 180),
    ]),
    ("network", [
        ("nmap",     "--script=default,vuln -sV -p 21,22,23,25,53,80,110,139,143,443,445,3306,3389,5432,6379,8080,8443 {target}", 300),
    ]),
    ("auth", [
        # hydra — uses /opt/cyberpulse/passwords.txt written by tool_api.py on the
        # Kali VM at startup (separate filesystem from this worker container).
        # -l root: target root user. -f: stop on first hit. -V: show every attempt.
        # -w 5: 5s connection timeout. 120s hard cap on the whole phase.
        ("hydra",    "-l root -P /opt/cyberpulse/passwords.txt -t 4 -f -V -w 5 {target} ssh", 120),
    ]),
    ("ssl", [
        ("testssl.sh", "--jsonfile /tmp/ssl_{scan_id}.json {target}",         180),
    ]),
    ("osint", [
        ("theharvester", "-d {target} -b all -l 100",                         180),
        ("gitleaks",     "detect --source /tmp --no-git --report-format json", 60),
    ]),
]

PHASE_NAMES    = [p[0] for p in PHASES]
PHASE_DISPLAY  = {
    "recon":    "Phase 1 — Reconnaissance",
    "vuln_scan":"Phase 2 — Vulnerability Scan",
    "webapp":   "Phase 3 — Web Application Tests",
    "network":  "Phase 4 — Network Services",
    "auth":     "Phase 5 — Authentication Tests",
    "ssl":      "Phase 6 — SSL/TLS Analysis",
    "osint":    "Phase 7 — OSINT & Secrets",
}


_MODULE_DISPLAY = {
    "m09": "M09 — Business Logic Tester",
    "m10": "M10 — CVE Correlator",
    "m11": "M11 — Visual Recon",
    "m12": "M12 — Smart Credential Attack",
    "m13": "M13 — AI Adaptive Scanner",
    "m14": "M14 — Scan Comparator",
    "m15": "M15 — Autonomous Attack Agent",
    "m16": "M16 — Exploit Verificatie",
    "m17": "M17 — Cloud Scanner",
}


def _parse_hydra_findings(output: str) -> list[dict]:
    """Extract structured credential findings from hydra stdout."""
    import re as _re
    findings = []
    # Matches: [22][ssh] host: 192.168.121.170   login: root   password: toor
    pattern = _re.compile(
        r"\[(\d+)\]\[(\w+)\]\s+host:\s+\S+\s+login:\s+(\S+)\s+password:\s+(\S+)",
        _re.IGNORECASE,
    )
    for m in pattern.finditer(output):
        port, service, login, password = m.group(1), m.group(2), m.group(3), m.group(4)
        is_root = login.lower() in ("root", "admin", "administrator")
        findings.append({
            "type":        "credential_found",
            "severity":    "CRITICAL",
            "title":       f"Weak {service.upper()} credentials: {login}:{password}",
            "service":     service,
            "port":        int(port),
            "login":       login,
            "password":    password,
            "description": (
                f"Valid {service.upper()} credentials discovered on port {port}: "
                f"login='{login}', password='{password}'. "
                + ("Full root/administrator access to the target system is possible."
                   if is_root else "Authenticated access to the service is possible.")
            ),
            "impact": (
                f"An attacker can SSH into the target as '{login}' and gain "
                + ("unrestricted root control over the system, including reading all files, "
                   "installing backdoors, and pivoting to other systems."
                   if is_root else "authenticated access to the service.")
            ),
            "recommendation": (
                f"1. Immediately change the '{login}' password to a strong random value. "
                f"2. Disable direct root SSH login (set PermitRootLogin no in sshd_config). "
                f"3. Enforce SSH key-based authentication and disable password auth. "
                f"4. Review /etc/passwd and /etc/shadow for other weak passwords. "
                f"5. Check for persistence (crontabs, authorized_keys, new users)."
            ),
            "owasp": "A07:2021 - Identification and Authentication Failures",
            "cvss":  9.8,
        })
    return findings


def _run_cve_correlator(scan_id: str, target: str, all_outputs: dict, r) -> str:
    """Inline CVE correlation: extract service versions from nmap output and query NVD."""
    import re
    import requests as _req

    lines: list[str] = []
    lines.append(f"[M10] CVE Correlator — target: {target}")

    # Extract service/version lines from nmap output
    nmap_text = ""
    for phase_data in all_outputs.values():
        for tool_name, output in phase_data.items():
            if "nmap" in tool_name.lower() and output:
                nmap_text += output + "\n"

    # Parse "PORT/tcp open  service  version" lines
    svc_pattern = re.compile(
        r"(\d+)/tcp\s+open\s+(\S+)\s*(.*)", re.IGNORECASE
    )
    services = []
    for match in svc_pattern.finditer(nmap_text):
        port, service, version = match.group(1), match.group(2), match.group(3).strip()
        version_clean = re.split(r"\s{2,}|#", version)[0][:60]
        if version_clean:
            services.append({"port": port, "service": service, "version": version_clean})

    if not services:
        lines.append("[M10] Geen service-versies gevonden in nmap output — CVE lookup overgeslagen")
        return "\n".join(lines)

    lines.append(f"[M10] {len(services)} services gevonden, NVD opzoeken...")
    findings_found = 0

    for svc in services[:8]:  # cap at 8 to respect NVD rate limit
        keyword = f"{svc['service']} {svc['version']}"
        try:
            resp = _req.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params={"keywordSearch": keyword, "resultsPerPage": 3},
                timeout=10,
                headers={"User-Agent": "CyberPulse/1.0"},
            )
            if resp.status_code == 200:
                vulns = resp.json().get("vulnerabilities", [])
                for v in vulns:
                    cve_id = v.get("cve", {}).get("id", "?")
                    desc = next(
                        (d["value"][:120] for d in v.get("cve", {}).get("descriptions", []) if d.get("lang") == "en"),
                        ""
                    )
                    metrics = v.get("cve", {}).get("metrics", {})
                    score = 0.0
                    for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        if metrics.get(key):
                            score = float(metrics[key][0].get("cvssData", {}).get("baseScore", 0))
                            break
                    lines.append(f"  [{cve_id}] CVSS={score} port={svc['port']}/{svc['service']}: {desc}")
                    findings_found += 1
            import time as _time
            _time.sleep(0.6)
        except Exception as exc:
            lines.append(f"  [M10] NVD fout voor {keyword}: {exc}")

    lines.append(f"[M10] Klaar — {findings_found} CVEs gevonden voor {len(services)} services")
    return "\n".join(lines)


def _run_visual_recon(target: str) -> str:
    """M11 — Visual Recon: probe for exposed sensitive files over HTTP."""
    import requests as _req

    paths = [
        "/.git/HEAD", "/.env", "/config.php", "/wp-config.php", "/phpinfo.php",
        "/info.php", "/.htaccess", "/robots.txt", "/sitemap.xml",
    ]

    base = target if target.startswith("http") else f"http://{target}"
    base = base.rstrip("/")

    lines: list[str] = ["[M11] Visual Recon — gevoelige bestanden controle"]
    disallow_entries: list[str] = []
    found_count = 0

    # Quick connectivity probe — if the webserver isn't reachable, skip all paths
    # and show one clean line instead of a raw exception per path.
    try:
        _req.get(base + "/", timeout=5, verify=False,
                 headers={"User-Agent": "CyberPulse/1.0"})
    except Exception:
        lines.append("[M11] Poort 80 niet open — webserver niet bereikbaar op dit doel")
        return "\n".join(lines)

    for path in paths:
        url = f"{base}{path}"
        try:
            resp = _req.get(
                url, timeout=5, verify=False, allow_redirects=False,
                headers={"User-Agent": "CyberPulse/1.0"},
            )
            status = resp.status_code
            body = resp.text or ""

            if path == "/.git/HEAD" and status == 200 and body.lstrip().startswith("ref:"):
                found_count += 1
                lines.append(f"  {path} → {status} ⚠️ GIT BLOOTGESTELD (Git repository blootgesteld)")
            elif status == 200:
                found_count += 1
                lines.append(f"  {path} → {status} ⚠️ GEVONDEN")
            else:
                lines.append(f"  {path} → {status}")

            if path == "/robots.txt" and status == 200:
                for raw in body.splitlines():
                    stripped = raw.strip()
                    if stripped.lower().startswith("disallow:"):
                        entry = stripped.split(":", 1)[1].strip()
                        if entry:
                            disallow_entries.append(entry)
        except Exception:
            # Never leak raw Python exceptions — keep it clean and Dutch.
            lines.append(f"  {path} → niet bereikbaar")

    lines.append(f"[M11] {found_count} gevoelige bestand(en) blootgesteld.")
    if disallow_entries:
        lines.append("Disallow-regels in robots.txt:")
        for entry in disallow_entries:
            lines.append(f"  - {entry}")

    return "\n".join(lines)


def _run_smart_credential(scan_id: str, target: str, all_outputs: dict, runner) -> str:
    """M12 — Smart Credential Attack: build a target-specific wordlist and run hydra."""
    lines: list[str] = ["[M12] Smart Credential Attack — doelspecifieke aanval"]
    try:
        import re as _re
        import ipaddress as _ip

        # Build combined output but DROP error/stderr lines so they can never be
        # mistaken for a page title (e.g. "[STDERR] ERROR ... Connection refused").
        _DROP = ("stderr", "error", "connection refused", "refused", "warning")
        combined = ""
        for phase_data in all_outputs.values():
            for output in phase_data.values():
                if not output:
                    continue
                for raw in output.splitlines():
                    if any(d in raw.lower() for d in _DROP):
                        continue
                    combined += raw + "\n"

        # Definitive blocklist — any extracted name containing one of these
        # substrings, or exactly matching a common stop-word, is rejected.
        _BLOCK_SUBSTR = (
            "info", "stderr", "error", "warning", "connection", "refused",
            "failed", "timeout", "none", "null", "unknown", "undefined",
            "http", "https", "ftp", "ssh", "tcp", "udp", "ssl", "tls",
            "nikto", "nmap", "sqlmap", "nuclei", "hydra", "ffuf", "whatweb",
            "404", "403", "401", "500", "200", "301", "302",
            "target", "host", "port", "scan", "test", "debug",
            "localhost", "server", "client", "socket",
        )
        _BLOCK_EXACT = {
            "the", "and", "or", "not", "with", "from", "this", "that",
            "voor", "van", "met", "het", "een", "niet", "maar", "zijn",
        }

        def _bad_name(s: str) -> bool:
            sl = s.lower()
            if len(sl) <= 4:                      # min length > 4
                return True
            if not any(c.isalpha() for c in sl):  # must contain a letter
                return True
            if sl in _BLOCK_EXACT:
                return True
            if any(b in sl for b in _BLOCK_SUBSTR):
                return True
            return False

        name = ""
        source = "standaard"

        # 1) whatweb Title[...]  → 2) any bracketed page title in httpx output
        m = _re.search(r"Title\[([^\]]+)\]", combined)
        if not m:
            m = _re.search(r"\[([A-Za-z][^\]]{2,60})\]", combined)
        if m:
            token = next(
                (w for w in _re.split(r"[\s:|/]+", m.group(1)) if w and w[0].isalpha()),
                "",
            )
            cleaned = _re.sub(r"[^a-zA-Z0-9]", "", token).lower()
            if cleaned and not _bad_name(cleaned):
                name = cleaned
                source = "paginatitel"

        # 3) domain name (only when the target is NOT a pure IP)
        is_ip = True
        if not name:
            host = target.split("://")[-1].split("/")[0].split(":")[0]
            try:
                _ip.ip_address(host)
            except ValueError:
                is_ip = False
            if not is_ip and "." in host:
                cleaned = _re.sub(r"[^a-zA-Z0-9]", "", host.split(".")[0]).lower()
                if cleaned and not _bad_name(cleaned):
                    name = cleaned
                    source = "domeinnaam"

        # 4) No valid name survived filtering → definitive generic fallback.
        if not name:
            lines.append("[M12] Geen geldige bedrijfsnaam gevonden — standaard aanval op gebruiker 'admin'")

        # Username to brute-force: a name rarely is the login, default to admin.
        username = "admin"

        # Name-derived passwords only if we found a meaningful, validated name.
        name_words = (
            [name, name + "123", name + "2024", name + "2025", name + "@123",
             name.capitalize() + "!"]
            if name else []
        )
        base_words = [
            "admin", "administrator", "welkom01", "Welkom01!",
            "welkom2024", "Welkom2024!", "test", "test123",
            "password", "Password1!", "changeme", "root", "ubuntu", "kali",
        ]
        words = list(dict.fromkeys(name_words + base_words))  # dedupe, keep order

        lines.append(f"[M12] Gebruikte naam: '{name or '(geen)'}' uit {source}")
        lines.append(f"[M12] Wordlist met {len(words)} wachtwoorden, gebruiker '{username}'.")

        wl = "\\n".join(words)
        wordlist_path = f"/opt/cyberpulse/custom_{scan_id}.txt"
        runner.run_safe(
            "bash",
            f"-c \"mkdir -p /opt/cyberpulse && printf '{wl}\\n' > {wordlist_path}\"",
            10,
        )

        result = runner.run_safe(
            "hydra",
            f"-l {username} -P {wordlist_path} -t 4 -f -V {target} ssh",
            120,
        )
        hydra_out = result.stdout or (result.stderr or "")

        creds = _parse_hydra_findings(hydra_out)
        if creds:
            lines.append(f"[M12] Doelspecifieke credentials GEVONDEN ({len(creds)}):")
            for c in creds:
                lines.append(f"  {c['login']}:{c['password']} via {c['service']}:{c['port']}")
        else:
            lines.append("[M12] Geen doelspecifieke credentials gevonden.")

        tail = "\n".join(hydra_out.strip().splitlines()[-8:])
        if tail:
            lines.append("[M12] Hydra output (laatste regels):")
            lines.append(tail)
    except Exception as exc:
        lines.append(f"[M12] Fout tijdens uitvoering: {exc}")

    return "\n".join(lines)


def _run_scan_comparator(scan_id: str, target: str, db, scan) -> str:
    """M14 — Scan Comparator: diff the current scan against the previous one for this target."""
    try:
        prev = (
            db.query(Scan)
            .filter(
                Scan.target_id == scan.target_id,
                Scan.id != scan.id,
                Scan.status == "completed",
            )
            .order_by(Scan.created_at.desc())
            .first()
        )

        if not prev:
            return "[M14] Eerste scan voor dit doel — geen vergelijking mogelijk."

        def _key(f: dict) -> str:
            return f"{f.get('title', '')}|{f.get('severity', '')}"

        curr_findings = scan.findings or []
        prev_findings = prev.findings or []

        curr_map = {_key(f): f for f in curr_findings if isinstance(f, dict)}
        prev_map = {_key(f): f for f in prev_findings if isinstance(f, dict)}

        new_keys = [k for k in curr_map if k not in prev_map]
        fixed_keys = [k for k in prev_map if k not in curr_map]
        unchanged_keys = [k for k in curr_map if k in prev_map]

        prev_risk = round(100 - (prev.security_score or 100))
        curr_risk = round(100 - (scan.security_score or 100))
        delta = curr_risk - prev_risk
        delta_str = f"+{delta}" if delta > 0 else str(delta)

        lines: list[str] = [
            f"[M14] Vergelijking met scan van {prev.created_at:%d-%m-%Y}:",
            f"Risicoscore: {prev_risk} → {curr_risk} ({delta_str})",
            "",
            f"🆕 NIEUW ({len(new_keys)}):",
        ]
        for k in new_keys:
            lines.append(f"  - {curr_map[k].get('title', k)}")
        lines.append(f"✅ OPGELOST ({len(fixed_keys)}):")
        for k in fixed_keys:
            lines.append(f"  - {prev_map[k].get('title', k)}")
        lines.append(f"⚪ ONGEWIJZIGD ({len(unchanged_keys)})")

        return "\n".join(lines)
    except Exception as exc:
        return f"[M14] Vergelijking niet mogelijk door fout: {exc}"


def _run_business_logic(target: str) -> str:
    """M09 — Business Logic Tester: probe admin/sensitive endpoints + rate limiting."""
    lines: list[str] = ["[M09] Business Logic Tester — endpoint & rate-limit controle"]
    try:
        import requests as _req
        base = target if target.startswith("http") else f"http://{target}"
        base = base.rstrip("/")
        paths = [
            "/admin", "/administrator", "/dashboard", "/api/admin", "/api/users",
            "/backup", "/config", "/.env", "/phpinfo.php", "/server-status",
            "/.git/config", "/wp-admin",
        ]
        exposed = 0
        for p in paths:
            try:
                r = _req.get(base + p, timeout=5, verify=False, allow_redirects=False,
                             headers={"User-Agent": "CyberPulse/1.0"})
                if r.status_code == 200:
                    exposed += 1
                    lines.append(f"  {p} → 200 ⚠️ TOEGANKELIJK")
                elif r.status_code == 403:
                    exposed += 1
                    lines.append(f"  {p} → 403 (bestaat, afgeschermd)")
                else:
                    lines.append(f"  {p} → {r.status_code}")
            except Exception:
                lines.append(f"  {p} → geen verbinding")

        # Rate-limit test: 20 snelle verzoeken
        codes = []
        try:
            for _ in range(20):
                rr = _req.get(base + "/", timeout=3, verify=False)
                codes.append(rr.status_code)
        except Exception:
            pass
        if codes and 429 not in codes and 503 not in codes:
            lines.append(f"[M09] Ratelimiting: NIET GEDETECTEERD ⚠️ ({len(codes)} snelle verzoeken, geen 429/503)")
        elif codes:
            lines.append("[M09] Ratelimiting: gedetecteerd (429/503 ontvangen)")
        else:
            lines.append("[M09] Ratelimiting: geen webserver bereikbaar")
        lines.append(f"[M09] {exposed} interessante endpoint(s) gevonden.")
    except Exception as exc:
        lines.append(f"[M09] Fout tijdens uitvoering: {exc}")
    return "\n".join(lines)


def _run_ai_adaptive(scan_id: str, target: str, all_outputs: dict, runner) -> str:
    """M13 — AI Adaptive Scanner: ask DeepSeek for 3 follow-up tests and run safe ones."""
    lines: list[str] = ["[M13] AI Adaptive Scanner — DeepSeek vervolgtests"]
    try:
        if not settings.deepseek_api_key:
            lines.append("[M13] DeepSeek API-sleutel niet geconfigureerd — overgeslagen.")
            return "\n".join(lines)

        import json as _json
        from openai import OpenAI

        summary = ""
        for phase, tools in all_outputs.items():
            for tname, out in tools.items():
                if out:
                    summary += f"\n## {phase}/{tname}\n{out[:800]}"
        summary = summary[:3000] or "(geen eerdere output)"

        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        prompt = (
            f"You are a penetration tester. Based on these scan results for {target}:\n{summary}\n\n"
            "Suggest exactly 3 additional specific security tests. "
            "Respond ONLY with a JSON array, no markdown, no explanation, no code blocks. "
            'Just the raw JSON: [{"test":"name","command":"cmd using the target","reason":"why"}]'
        )

        logger.info("[%s] M13: sending %d chars to DeepSeek", scan_id, len(prompt))
        try:
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2, max_tokens=700, timeout=30,
            )
        except Exception as call_exc:
            msg = str(call_exc).lower()
            logger.warning("[%s] M13: DeepSeek call failed: %s", scan_id, call_exc)
            if "timeout" in msg or "timed out" in msg:
                lines.append("[M13] Timeout — AI niet bereikbaar binnen 30 seconden")
            else:
                lines.append("[M13] AI-analyse tijdelijk niet beschikbaar — probeer opnieuw")
            return "\n".join(lines)

        raw = (resp.choices[0].message.content or "").strip()
        logger.info("[%s] M13: raw response: %s", scan_id, raw[:500])

        # Strip markdown code fences (```json ... ```), then isolate the JSON array.
        clean = raw
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.lstrip().lower().startswith("json"):
                clean = clean.lstrip()[4:]
        clean = clean.strip()
        if not clean.startswith("["):
            s, e = clean.find("["), clean.rfind("]") + 1
            if s >= 0 and e > 0:
                clean = clean[s:e]

        try:
            suggestions = _json.loads(clean)
            if not isinstance(suggestions, list):
                raise ValueError("response is not a JSON array")
        except Exception as parse_exc:
            logger.warning("[%s] M13: JSON parse failed: %s | raw=%s", scan_id, parse_exc, raw[:300])
            lines.append("[M13] AI-analyse tijdelijk niet beschikbaar — probeer opnieuw")
            return "\n".join(lines)

        lines.append(f"[M13] {len(suggestions)} AI-aanbevolen tests:")
        allowed = {"nmap", "nuclei", "nikto", "curl", "httpx-pd", "whatweb"}
        for i, s in enumerate(suggestions[:3], 1):
            test = s.get("test", "test")
            reason = s.get("reason", "")
            command = s.get("command", "")
            lines.append(f"{i}. {test}: {reason}")
            lines.append(f"   Commando: {command}")
            parts = command.split()
            tool = parts[0] if parts else ""
            if tool in allowed:
                args = " ".join(parts[1:]).replace("{target}", target)
                res = runner.run_safe(tool, args, 60)
                out = (res.stdout or res.stderr or "").strip()
                lines.append(f"   Resultaat ({len(out)} bytes): {out[:300]}")
            else:
                lines.append(f"   (tool '{tool}' niet automatisch uitgevoerd)")
    except Exception as exc:
        lines.append(f"[M13] Fout: {exc}")
    return "\n".join(lines)


# Tools M15/M17 are allowed to run; everything else (and any shell metachar) is blocked.
_M15_ALLOWED_TOOLS = {"nmap", "curl", "httpx-pd", "nuclei", "ffuf", "nikto", "whatweb", "sqlmap", "gitleaks"}
_FORBIDDEN_TOKENS = ("rm ", "wget", "chmod", "python", "bash", " sh ", "nc ", "netcat",
                     "/bin/", ";", "&&", "||", "|", "`", "$(", ">", "<", "&")


def _safe_chain_command(tool: str, args: str) -> bool:
    if tool not in _M15_ALLOWED_TOOLS:
        return False
    blob = f" {tool} {args} ".lower()
    return not any(tok in blob for tok in _FORBIDDEN_TOKENS)


def _run_attack_agent(scan_id: str, target: str, all_outputs: dict, runner) -> str:
    """M15 — Autonomous Attack Agent: DeepSeek chains findings into a safe attack path."""
    lines: list[str] = ["[M15] Autonomous Attack Agent — aanvalsketen analyse"]
    try:
        if not settings.deepseek_api_key:
            lines.append("[M15] DeepSeek niet geconfigureerd — overgeslagen.")
            return "\n".join(lines)
        import json as _json
        from openai import OpenAI

        context = ""
        for phase, tools in all_outputs.items():
            for tname, out in tools.items():
                if out:
                    context += f"\n## {phase}/{tname}\n{out[:600]}"
        context = context[:4000] or "(geen output)"

        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        system = (
            "You are an expert penetration tester. Based on scan results, generate an attack chain. "
            "Respond ONLY with a raw JSON object, no markdown, no code blocks: "
            '{"objective":"...","steps":[{"step":1,"name":"...","tool":"nmap|curl|httpx-pd|nuclei|ffuf|nikto|whatweb|sqlmap|gitleaks",'
            '"command":"exact command with {target}","depends_on":"...","success_indicator":"..."}]} '
            "Maximum 5 steps. Only read-only, non-destructive commands. No shell operators."
        )
        user = f"Target: {target}\nScan results:\n{context}"

        logger.info("[%s] M15 starting", scan_id)
        try:
            resp = client.chat.completions.create(
                model=settings.deepseek_model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
                temperature=0.2, max_tokens=900, timeout=30,
            )
        except Exception as call_exc:
            msg = str(call_exc).lower()
            lines.append("[M15] Timeout — AI niet bereikbaar binnen 30 seconden"
                         if ("timeout" in msg or "timed out" in msg)
                         else "[M15] AI tijdelijk niet beschikbaar — probeer opnieuw")
            return "\n".join(lines)

        raw = (resp.choices[0].message.content or "").strip()
        clean = raw
        if clean.startswith("```"):
            parts = clean.split("```")
            clean = parts[1] if len(parts) > 1 else clean
            if clean.lstrip().lower().startswith("json"):
                clean = clean.lstrip()[4:]
        clean = clean.strip()
        if not clean.startswith("{"):
            s, e = clean.find("{"), clean.rfind("}") + 1
            if s >= 0 and e > 0:
                clean = clean[s:e]
        try:
            plan = _json.loads(clean)
        except Exception:
            logger.warning("[%s] M15: JSON parse failed | raw=%s", scan_id, raw[:300])
            lines.append("[M15] Geen geldig aanvalsplan ontvangen — probeer opnieuw")
            return "\n".join(lines)

        objective = plan.get("objective", "onbekend")
        steps = plan.get("steps", [])[:5]
        lines.append(f"[M15] Doel: {objective}")
        succeeded = 0
        for st in steps:
            num = st.get("step", "?")
            name = st.get("name", "stap")
            command = st.get("command", "")
            indicator = st.get("success_indicator", "")
            lines.append(f"[M15] Stap {num}: {name}")
            lines.append(f"  Commando: {command}")
            parts = command.split()
            cmd_tool = parts[0] if parts else (st.get("tool") or "")
            args = " ".join(parts[1:]).replace("{target}", target) if len(parts) > 1 else ""
            if not _safe_chain_command(cmd_tool, args):
                lines.append("  Status: OVERGESLAGEN (onveilig/niet-toegestaan commando) ✗")
                continue
            res = runner.run_safe(cmd_tool, args, 30)
            out = (res.stdout or res.stderr or "").strip()
            ok = bool(indicator) and indicator.lower()[:40] in out.lower()
            lines.append(f"  Resultaat: {out[:300]}")
            lines.append(f"  Status: {'GELUKT ✓' if ok else 'MISLUKT ✗'}")
            if ok:
                succeeded += 1
        lines.append(f"[M15] Aanvalsketen voltooid — {succeeded} van {len(steps)} stappen geslaagd")
        logger.info("[%s] M15 done — %d steps", scan_id, len(steps))
    except Exception as exc:
        logger.exception("[%s] M15 failed", scan_id)
        lines.append(f"[M15] Attack agent niet beschikbaar — {exc}")
    return "\n".join(lines)


def _run_metasploit_verify(scan_id: str, target: str, all_outputs: dict, runner) -> str:
    """M16 — Metasploit Verification: for M10 CVEs, run Metasploit `check` (non-destructive)."""
    lines: list[str] = ["[M16] Metasploit Verificatie — exploit controle"]
    try:
        import re as _re
        m10_text = ""
        for v in (all_outputs.get("m10", {}) or {}).values():
            if v:
                m10_text += v + "\n"
        cves = list(dict.fromkeys(_re.findall(r"CVE-\d{4}-\d{4,}", m10_text)))[:3]
        if not cves:
            lines.append("[M16] Geen CVEs van M10 om te verifiëren.")
            return "\n".join(lines)

        logger.info("[%s] M16 starting — %d CVEs", scan_id, len(cves))
        # Availability probe
        probe = runner.run_safe("msfconsole", "-v", 20)
        probe_blob = ((probe.stdout or "") + (probe.stderr or "") + (getattr(probe, "error", "") or "")).lower()
        if "not found" in probe_blob or (not probe.stdout and "framework" not in probe_blob and not probe.success):
            lines.append("[M16] Metasploit niet beschikbaar op Kali VM")
            lines.append("[M16] Installeer met: apt-get install metasploit-framework")
            return "\n".join(lines)

        proven = 0
        for cve in cves:
            lines.append(f"[M16] {cve}:")
            search = runner.run_safe("msfconsole", f"-q -x \"search cve:{cve}; exit\"", 60)
            sout = (search.stdout or "") + (search.stderr or "")
            mod = _re.search(r"(exploit/\S+)", sout)
            if not mod:
                lines.append("  Module: geen Metasploit-module gevonden")
                continue
            module = mod.group(1)
            lines.append(f"  Module: {module}")
            chk = runner.run_safe(
                "msfconsole",
                f"-q -x \"use {module}; set RHOSTS {target}; check; exit\"",
                90,
            )
            cl = ((chk.stdout or "") + (chk.stderr or "")).lower()
            if "is vulnerable" in cl and "not vulnerable" not in cl:
                proven += 1
                lines.append("  Status: BEWEZEN KWETSBAAR ⚠️")
                lines.append("  (Geen exploitatie uitgevoerd — check-only modus)")
            elif "not vulnerable" in cl:
                lines.append("  Status: Niet kwetsbaar op dit systeem ✓")
            elif "does not support check" in cl:
                lines.append("  Status: ONBEKEND (module ondersteunt check niet)")
            else:
                lines.append("  Status: NIET GETEST")
        lines.append(f"[M16] Samenvatting: {len(cves)} CVEs getest, {proven} bewezen kwetsbaar")
        logger.info("[%s] M16 done — %d proven", scan_id, proven)
    except Exception as exc:
        logger.exception("[%s] M16 failed", scan_id)
        lines.append(f"[M16] Verificatie niet beschikbaar — {exc}")
    return "\n".join(lines)


def _run_cloud_scanner(scan_id: str, target: str, all_outputs: dict, scan, runner) -> str:
    """M17 — Cloud Security Scanner: passive cloud-misconfig detection (+ optional creds)."""
    lines: list[str] = ["[M17] Cloud Security Scanner"]
    try:
        import re as _re
        import requests as _req

        blob = ""
        for tools in all_outputs.values():
            for out in tools.values():
                if out:
                    blob += out + "\n"
        bl = blob.lower()
        if "amazonaws.com" in bl or "ec2" in bl or "169.254.169.254" in bl:
            provider = "AWS"
        elif "azure" in bl or "azurewebsites.net" in bl or "cloudapp.azure" in bl:
            provider = "Azure"
        elif "googleapis.com" in bl or "appspot.com" in bl or "metadata.google" in bl:
            provider = "GCP"
        else:
            provider = "Onbekend"
        lines.append(f"[M17] Cloud provider gedetecteerd: {provider}")

        findings = 0
        base = target if target.startswith("http") else f"http://{target}"
        base = base.rstrip("/")

        # Exposed metadata endpoints proxied through the target
        for p in ("/latest/meta-data/", "/metadata/instance", "/computeMetadata/v1/"):
            try:
                r = _req.get(base + p, timeout=5, verify=False,
                             headers={"Metadata-Flavor": "Google", "Metadata": "true"})
                if r.status_code == 200 and r.text.strip():
                    findings += 1
                    lines.append(f"[M17] Metadata endpoint {p}: BEREIKBAAR ⚠️ KRITIEK")
            except Exception:
                pass

        # Cloud-orchestration ports from nmap output
        nmap_text = ""
        for tname_tools in all_outputs.values():
            for tname, out in tname_tools.items():
                if "nmap" in tname.lower() and out:
                    nmap_text += out + "\n"
        port_svc = {"2375": "Docker API", "2376": "Docker API", "6443": "Kubernetes API",
                    "10250": "Kubelet API", "8500": "Consul", "2379": "etcd", "4001": "etcd"}
        for port, svc in port_svc.items():
            if _re.search(rf"\b{port}/tcp\s+open", nmap_text):
                findings += 1
                lines.append(f"[M17] Poort {port} open: {svc} blootgesteld ⚠️")

        # Optional active scan with user-supplied credentials (never persisted)
        creds = (scan.config or {}).get("cloud_credentials") or {}
        if creds.get("aws_access_key") and creds.get("aws_secret_key"):
            lines.append("[M17] AWS credentials aanwezig — actieve scan...")
            try:
                import boto3  # type: ignore
                sess = boto3.session.Session(
                    aws_access_key_id=creds["aws_access_key"],
                    aws_secret_access_key=creds["aws_secret_key"],
                    region_name=creds.get("aws_region", "eu-west-1"),
                )
                s3 = sess.client("s3")
                buckets = s3.list_buckets().get("Buckets", [])
                lines.append(f"[M17] {len(buckets)} S3-buckets gevonden")
                ec2 = sess.client("ec2")
                for sg in ec2.describe_security_groups().get("SecurityGroups", []):
                    for perm in sg.get("IpPermissions", []):
                        for rng in perm.get("IpRanges", []):
                            if rng.get("CidrIp") == "0.0.0.0/0":
                                findings += 1
                                lines.append(f"[M17] Security group {sg.get('GroupId')}: open voor internet ⚠️")
            except ImportError:
                lines.append("[M17] boto3 niet geïnstalleerd — actieve AWS-scan overgeslagen")
            except Exception as exc:
                lines.append(f"[M17] AWS-scan fout: {exc}")

        if findings == 0:
            lines.append("[M17] Geen cloud misconfiguraties gevonden ✓")
        lines.append(f"[M17] Samenvatting: {findings} bevinding(en)")
        logger.info("[%s] M17 done — %d findings", scan_id, findings)
    except Exception as exc:
        logger.exception("[%s] M17 failed", scan_id)
        lines.append(f"[M17] Cloud scanner niet beschikbaar — {exc}")
    return "\n".join(lines)


def _should_run_phase(phase_name: str, scan_mode: str, phases_enabled: list | None) -> bool:
    # Auth phase runs in ALL modes — blackbox uses default wordlists,
    # graybox/whitebox use provided credentials (substituted in args template).
    # If user specified custom phases, only run those.
    if phases_enabled:
        return phase_name in phases_enabled
    return True


@celery_app.task(name="app.workers.scan_tasks.run_scan", bind=True, max_retries=2)
def run_scan(self, scan_id: str):
    """Full 8-phase scan orchestration via the Kali VM scanner API."""
    logger.info("Starting scan %s", scan_id)
    r = _redis()
    runner = _runner()

    with Session(sync_engine) as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return

        target_obj = db.query(Target).filter(Target.id == scan.target_id).first()
        if not target_obj:
            logger.error("Target for scan %s not found", scan_id)
            scan.status = "failed"
            db.commit()
            return

        target = target_obj.value

        # Pull scan context from config JSONB (set at scan creation)
        config      = scan.config or {}
        scan_mode   = config.get("scan_mode",    scan.scan_mode or "blackbox")
        credentials = config.get("credentials",  scan.credentials or {})
        phases_enabled = config.get("phases_enabled", scan.phases_enabled)

        # Persist resolved context to new dedicated columns
        scan.scan_mode   = scan_mode
        scan.credentials = credentials

        # Check Kali VM reachability
        if not runner.health_check():
            logger.error("Kali VM unreachable for scan %s", scan_id)
            _pub(r, scan_id, {"type": "error", "message": f"Kali VM ({settings.kali_vm_host}:{settings.kali_vm_port}) is not reachable. Make sure tool_api.py is running."})
            scan.status = "failed"
            db.commit()
            return

        scan.status     = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.phases_completed = []
        scan.tool_outputs     = {}
        db.commit()

        _pub(r, scan_id, {
            "type":    "scan_start",
            "target":  target,
            "mode":    scan_mode,
            "phases":  PHASE_NAMES,
            "timestamp": time.time(),
        })

        all_outputs: dict[str, dict[str, str]] = {}

        for phase_num, (phase_name, phase_tools) in enumerate(PHASES, start=1):
            if not _should_run_phase(phase_name, scan_mode, phases_enabled):
                _pub(r, scan_id, {
                    "type": "phase_skip", "phase": phase_name, "phase_num": phase_num,
                    "reason": "disabled by scan mode or user selection",
                })
                continue

            scan.current_phase     = phase_name
            scan.current_phase_num = phase_num
            scan.progress          = int(((phase_num - 1) / len(PHASES)) * 80)
            db.commit()

            _pub(r, scan_id, {
                "type": "phase_start", "phase": phase_name, "phase_num": phase_num,
                "display": PHASE_DISPLAY.get(phase_name, phase_name),
                "progress": scan.progress, "timestamp": time.time(),
            })

            phase_outputs: dict[str, str] = {}

            for tool_name, args_template, timeout in phase_tools:
                args = (
                    args_template
                    .replace("{target}", target)
                    .replace("{scan_id}", str(scan_id))
                    .replace("{username}", credentials.get("username", "admin"))
                    .replace("{password}", credentials.get("password", ""))
                    .replace("{bearer_token}", credentials.get("bearer_token", ""))
                )

                # For graybox: if credentials provided for hydra, use them
                if phase_name == "auth" and tool_name == "hydra" and credentials.get("username"):
                    args = (
                        f"-l {credentials['username']} "
                        f"-p {credentials.get('password','password')} "
                        f"-t 4 {target} ssh"
                    )

                logger.info(
                    "[%s] %s/%s → command: %s %s",
                    scan_id, phase_name, tool_name, tool_name, args[:300],
                )
                _pub(r, scan_id, {
                    "type": "tool_start", "phase": phase_name,
                    "tool": tool_name, "timestamp": time.time(),
                })

                result = runner.run_safe(tool_name, args, timeout)

                output = result.stdout or (f"[STDERR] {result.stderr}" if result.stderr else "")
                if not result.success and result.error:
                    output = f"[ERROR] {result.error}\n{output}"

                logger.info(
                    "[%s] %s/%s done — success=%s duration=%.1fs output_bytes=%d",
                    scan_id, phase_name, tool_name,
                    result.success, result.duration_s, len(output),
                )
                if output:
                    logger.info("[%s] %s/%s output[:1000]:\n%s",
                                scan_id, phase_name, tool_name, output[:1000])
                else:
                    logger.warning("[%s] %s/%s produced NO output (tool missing on Kali VM?)",
                                   scan_id, phase_name, tool_name)

                phase_outputs[tool_name] = output

                # Parse structured credential findings from hydra output
                # so the AI receives them as explicit CRITICAL findings.
                if tool_name == "hydra" and output:
                    hydra_creds = _parse_hydra_findings(output)
                    if hydra_creds:
                        phase_outputs["hydra_findings"] = json.dumps(hydra_creds, ensure_ascii=False)
                        logger.info(
                            "[%s] auth/hydra: %d credential(s) found — %s",
                            scan_id, len(hydra_creds),
                            ", ".join(f"{c['login']}:{c['password']}@{c['service']}:{c['port']}" for c in hydra_creds),
                        )
                        _pub(r, scan_id, {
                            "type":    "credential_found",
                            "phase":   "auth",
                            "count":   len(hydra_creds),
                            "summary": ", ".join(f"{c['login']}:{c['password']} via {c['service']}:{c['port']}" for c in hydra_creds),
                            "timestamp": time.time(),
                        })

                _pub(r, scan_id, {
                    "type":     "tool_done",
                    "phase":    phase_name,
                    "tool":     tool_name,
                    "success":  result.success,
                    "duration": result.duration_s,
                    "output":   output[:2000],
                    "timestamp": time.time(),
                })

            all_outputs[phase_name] = phase_outputs

            # Persist phase outputs incrementally
            current_tool_outputs = scan.tool_outputs or {}
            current_tool_outputs[phase_name] = phase_outputs
            scan.tool_outputs     = current_tool_outputs
            completed = list(scan.phases_completed or [])
            completed.append(phase_name)
            scan.phases_completed = completed
            db.commit()

            # Also write to Redis for the analysis task
            for tool_name, output in phase_outputs.items():
                if output:
                    r.setex(f"scan:{scan_id}:output:{phase_name}:{tool_name}", 7200, output)

            _pub(r, scan_id, {
                "type": "phase_complete", "phase": phase_name, "phase_num": phase_num,
                "progress": int((phase_num / len(PHASES)) * 80), "timestamp": time.time(),
            })

        # ── Summary before AI analysis ────────────────────────────────────────
        total_output_bytes = sum(
            len(out)
            for phase_data in all_outputs.values()
            for out in phase_data.values()
        )
        phases_with_output = [
            phase for phase, tools in all_outputs.items()
            if any(len(o) > 10 for o in tools.values())
        ]
        logger.info(
            "[%s] Scan phases complete — %d phases ran, %d had output, %d total bytes collected",
            scan_id, len(all_outputs), len(phases_with_output), total_output_bytes,
        )
        if total_output_bytes == 0:
            logger.warning(
                "[%s] ALL TOOLS RETURNED EMPTY OUTPUT — check Kali VM tools are installed "
                "and tool_api.py is running on %s:%s",
                scan_id, settings.kali_vm_host, settings.kali_vm_port,
            )

        # ── Custom module phases (m09–m14) — run BEFORE AI analysis ───────────
        # so the AI analysis can use their output (e.g. M10's CVE data).
        CUSTOM_MODULES = {"m09", "m10", "m11", "m12", "m13", "m14", "m15", "m16", "m17"}
        custom_selected = [p for p in (scan.phases or []) if p in CUSTOM_MODULES]
        logger.info("[%s] Custom modules selected: %s", scan_id, custom_selected or "none")

        for mod_id in custom_selected:
            logger.info("[%s] Running custom module %s", scan_id, mod_id)
            _pub(r, scan_id, {
                "type": "phase_start", "phase": mod_id,
                "display": _MODULE_DISPLAY.get(mod_id, mod_id),
                "timestamp": time.time(),
            })
            logger.info("[%s] %s starting", scan_id, mod_id.upper())
            try:
                if mod_id == "m09":
                    mod_output = _run_business_logic(target)
                elif mod_id == "m10":
                    mod_output = _run_cve_correlator(scan_id, target, all_outputs, r)
                elif mod_id == "m11":
                    mod_output = _run_visual_recon(target)
                elif mod_id == "m12":
                    mod_output = _run_smart_credential(scan_id, target, all_outputs, runner)
                elif mod_id == "m13":
                    mod_output = _run_ai_adaptive(scan_id, target, all_outputs, runner)
                elif mod_id == "m14":
                    mod_output = _run_scan_comparator(scan_id, target, db, scan)
                elif mod_id == "m15":
                    mod_output = _run_attack_agent(scan_id, target, all_outputs, runner)
                elif mod_id == "m16":
                    mod_output = _run_metasploit_verify(scan_id, target, all_outputs, runner)
                elif mod_id == "m17":
                    mod_output = _run_cloud_scanner(scan_id, target, all_outputs, scan, runner)
                else:
                    mod_output = f"Module {mod_id} geselecteerd — nog niet geïmplementeerd."
            except Exception as exc:  # a module must NEVER crash the scan
                logger.exception("[%s] Custom module %s failed", scan_id, mod_id)
                mod_output = f"[{mod_id.upper()}] Module mislukt: {exc}"
            logger.info("[%s] %s done — output %d bytes", scan_id, mod_id.upper(), len(mod_output))

            all_outputs[mod_id] = {"module": mod_output}
            current_tool_outputs = scan.tool_outputs or {}
            current_tool_outputs[mod_id] = {"module": mod_output}
            scan.tool_outputs = current_tool_outputs
            completed = list(scan.phases_completed or [])
            completed.append(mod_id)
            scan.phases_completed = completed
            db.commit()

            # Emit the FULL module output as a tool_done event so the live
            # terminal renders every line (phase_complete alone showed nothing).
            _pub(r, scan_id, {
                "type":   "tool_done",
                "phase":  mod_id,
                "tool":   _MODULE_DISPLAY.get(mod_id, mod_id),
                "success": not mod_output.lower().startswith(f"[{mod_id}] module mislukt"),
                "duration": 0,
                "output": mod_output,
                "timestamp": time.time(),
            })
            _pub(r, scan_id, {
                "type": "phase_complete", "phase": mod_id,
                "output": mod_output, "timestamp": time.time(),
            })

        # ── Phase 8: AI Analysis (uses all phase + custom module output) ──────
        scan.status   = "analyzing"
        scan.progress = 85
        db.commit()

        _pub(r, scan_id, {
            "type": "phase_start", "phase": "ai_analysis", "phase_num": 8,
            "display": "Phase 8 — AI Analysis (DeepSeek)",
            "progress": 85, "timestamp": time.time(),
        })

        from app.workers.analysis_tasks import analyze_scan
        analyze_scan.delay(str(scan.id))


@celery_app.task(name="app.workers.scan_tasks.cleanup_containers")
def cleanup_containers():
    """No-op — kept for scheduler compatibility."""
    pass


_SCHEDULE_INTERVALS = {
    "daily":   60 * 60 * 24,
    "weekly":  60 * 60 * 24 * 7,
    "monthly": 60 * 60 * 24 * 30,
}


@celery_app.task(name="app.workers.scan_tasks.run_scheduled_scans")
def run_scheduled_scans():
    """Celery Beat runner — launch due scheduled scans (every 15 min).

    Defensive: any missing piece is logged and skipped; the task never raises.
    Only schedules whose target_ip maps to an existing Target (by value) are
    processed; others are skipped (target lookup/create is out of scope).
    """
    from datetime import timedelta

    try:
        now = datetime.now(timezone.utc)
        processed = 0

        with Session(sync_engine) as db:
            due = (
                db.query(ScheduledScan)
                .filter(
                    ScheduledScan.is_active == True,  # noqa: E712
                    ScheduledScan.next_run_at <= now,
                )
                .all()
            )

            for sched in due:
                try:
                    target = (
                        db.query(Target)
                        .filter(Target.value == sched.target_ip)
                        .first()
                    )
                    if not target:
                        logger.info(
                            "Scheduled scan %s skipped — no Target matches value '%s'",
                            sched.id, sched.target_ip,
                        )
                        continue

                    phases = sched.phases or list(PHASE_NAMES)
                    for mod in (sched.custom_modules or []):
                        if mod not in phases:
                            phases.append(mod)

                    scan = Scan(
                        status="pending",
                        scan_type="full",
                        phases=phases,
                        scan_mode="blackbox",
                        target_id=target.id,
                        user_id=sched.user_id,
                    )
                    db.add(scan)
                    db.commit()
                    db.refresh(scan)

                    run_scan.delay(str(scan.id))

                    interval = _SCHEDULE_INTERVALS.get(sched.schedule_type, _SCHEDULE_INTERVALS["weekly"])
                    sched.next_run_at = now + timedelta(seconds=interval)
                    sched.last_run_at = now
                    db.commit()
                    processed += 1
                except Exception as exc:
                    logger.warning("Scheduled scan %s failed to launch: %s", getattr(sched, "id", "?"), exc)
                    db.rollback()

        logger.info("Scheduled scan runner: processed %d scans", processed)
    except Exception as exc:
        logger.error("Scheduled scan runner error: %s", exc)
