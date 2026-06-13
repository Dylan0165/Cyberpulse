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
        except Exception as exc:
            lines.append(f"  {path} → fout ({exc})")

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

        # Extract a company/site name from earlier tool outputs (whatweb/httpx Title:)
        name = ""
        for phase_data in all_outputs.values():
            for output in phase_data.values():
                if not output:
                    continue
                for raw in output.splitlines():
                    if "Title:" in raw:
                        after = raw.split("Title:", 1)[1].strip()
                        token = after.split()[0] if after.split() else ""
                        if token:
                            name = token
                            break
                if name:
                    break
            if name:
                break

        if not name:
            name = target.split(".")[0].split("/")[-1]

        # Clean: lowercase, strip non-alphanumeric
        name = _re.sub(r"[^a-zA-Z0-9]", "", name).lower() or "admin"

        words = [
            name, name + "123", name + "2024", name + "2025", name + "@123",
            name.capitalize() + "!", "admin", "administrator", "test",
            "welkom01", "Welkom2024", "password", "toor",
        ]

        lines.append(f"[M12] Gebruikte naam: '{name}' — wordlist met {len(words)} wachtwoorden.")

        wl = "\\n".join(words)
        wordlist_path = f"/opt/cyberpulse/custom_{scan_id}.txt"
        runner.run_safe(
            "bash",
            f"-c \"mkdir -p /opt/cyberpulse && printf '{wl}\\n' > {wordlist_path}\"",
            10,
        )

        result = runner.run_safe(
            "hydra",
            f"-l admin -P {wordlist_path} -t 4 -f -V {target} ssh",
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
        CUSTOM_MODULES = {"m09", "m10", "m11", "m12", "m13", "m14"}
        custom_selected = [p for p in (scan.phases or []) if p in CUSTOM_MODULES]
        logger.info("[%s] Custom modules selected: %s", scan_id, custom_selected or "none")

        for mod_id in custom_selected:
            logger.info("[%s] Running custom module %s", scan_id, mod_id)
            _pub(r, scan_id, {
                "type": "phase_start", "phase": mod_id,
                "display": _MODULE_DISPLAY.get(mod_id, mod_id),
                "timestamp": time.time(),
            })
            mod_output = ""
            if mod_id == "m10":
                logger.info("[%s] M10 CVE Correlator starting", scan_id)
                mod_output = _run_cve_correlator(scan_id, target, all_outputs, r)
                logger.info("[%s] M10 CVE Correlator done — output %d bytes", scan_id, len(mod_output))
            elif mod_id == "m11":
                logger.info("[%s] M11 Visual Recon starting", scan_id)
                mod_output = _run_visual_recon(target)
                logger.info("[%s] M11 Visual Recon done — output %d bytes", scan_id, len(mod_output))
            elif mod_id == "m12":
                logger.info("[%s] M12 Smart Credential Attack starting", scan_id)
                mod_output = _run_smart_credential(scan_id, target, all_outputs, runner)
                logger.info("[%s] M12 Smart Credential Attack done — output %d bytes", scan_id, len(mod_output))
            elif mod_id == "m14":
                logger.info("[%s] M14 Scan Comparator starting", scan_id)
                mod_output = _run_scan_comparator(scan_id, target, db, scan)
                logger.info("[%s] M14 Scan Comparator done — output %d bytes", scan_id, len(mod_output))
            else:
                mod_output = f"Module {mod_id} geselecteerd — wordt in toekomstige versie geïntegreerd."
                logger.info("[%s] Custom module %s: not yet in pipeline", scan_id, mod_id)

            all_outputs[mod_id] = {"module": mod_output}
            current_tool_outputs = scan.tool_outputs or {}
            current_tool_outputs[mod_id] = {"module": mod_output}
            scan.tool_outputs = current_tool_outputs
            completed = list(scan.phases_completed or [])
            completed.append(mod_id)
            scan.phases_completed = completed
            db.commit()
            _pub(r, scan_id, {
                "type": "phase_complete", "phase": mod_id,
                "output": mod_output[:500], "timestamp": time.time(),
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
