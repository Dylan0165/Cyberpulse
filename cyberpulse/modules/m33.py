"""Module 33 — Privilege Escalation Vector Detection.

Identifies misconfigurations and information leaks that may allow
privilege escalation on web applications and servers.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m33")

# Admin endpoints to probe
ADMIN_PATHS = [
    "/admin", "/admin/", "/administrator", "/wp-admin",
    "/panel", "/cpanel", "/management", "/manager",
    "/admin/dashboard", "/admin/config", "/admin/settings",
    "/admin/users", "/admin/logs", "/debug", "/console",
    "/phpmyadmin", "/server-status", "/server-info",
    "/.env", "/config.php", "/web.config", "/wp-config.php",
    "/api/admin", "/api/v1/admin", "/api/internal",
    "/graphql", "/swagger", "/api-docs",
    "/actuator", "/actuator/env", "/actuator/health",
    "/metrics", "/trace", "/jolokia",
]

# Headers suggesting privilege info
PRIV_HEADERS = [
    "x-powered-by", "server", "x-aspnet-version",
    "x-debug", "x-debug-token", "x-runtime",
]


class Scanner:
    name = "Privilege Escalation Vectors"
    phase = "exploitation"
    description = "Identifies misconfigurations enabling privilege escalation"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Privilege escalation vector scan for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Admin panel discovery
        raw_lines.append("\n[Phase 1: Admin Panel Discovery]")
        for path in ADMIN_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 403):
                    sev = "high" if resp.status_code == 200 else "medium"
                    findings.append({
                        "type": "admin_panel",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"Admin panel at {path} (HTTP {resp.status_code})",
                        "severity": sev,
                    })
                    raw_lines.append(f"  {'HIGH' if sev == 'high' else 'MEDIUM'}: {path} — HTTP {resp.status_code}")
            except Exception:
                continue

        # Phase 2: IDOR checks (horizontal privilege escalation)
        raw_lines.append("\n[Phase 2: IDOR Detection]")
        idor_paths = [
            "/api/users/1", "/api/users/2",
            "/api/user/1", "/api/user/2",
            "/user/profile?id=1", "/user/profile?id=2",
            "/account?id=1", "/order/1", "/invoice/1",
        ]
        for path in idor_paths:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if any(k in data for k in ("email", "password", "username", "role", "admin")):
                            findings.append({
                                "type": "idor",
                                "path": path,
                                "detail": f"IDOR — sensitive data accessible at {path}",
                                "severity": "high",
                            })
                            raw_lines.append(f"  HIGH: IDOR at {path}")
                    except Exception:
                        pass
            except Exception:
                continue

        # Phase 3: Role manipulation via parameter tampering
        raw_lines.append("\n[Phase 3: Role Manipulation Checks]")
        role_endpoints = [
            ("/api/user/update", {"role": "admin"}),
            ("/api/user/update", {"is_admin": True}),
            ("/api/profile", {"role": "administrator"}),
            ("/api/settings", {"privilege": "root"}),
        ]
        for endpoint, body in role_endpoints:
            url = base_url + endpoint
            try:
                resp = self.session.post(url, json=body, timeout=8)
                if resp.status_code in (200, 201):
                    try:
                        data = resp.json()
                        if data.get("role") in ("admin", "administrator") or data.get("is_admin"):
                            findings.append({
                                "type": "role_manipulation",
                                "endpoint": endpoint,
                                "detail": f"Role escalation possible via {endpoint}",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: Role manipulation at {endpoint}")
                    except Exception:
                        pass
            except Exception:
                continue

        # Phase 4: Debug / diagnostic endpoints
        raw_lines.append("\n[Phase 4: Debug Endpoints]")
        debug_paths = [
            "/debug", "/_debug", "/trace", "/metrics",
            "/actuator", "/actuator/env", "/actuator/configprops",
            "/api/debug", "/api/status", "/api/info",
            "/elmah.axd", "/phpinfo.php", "/info.php",
            "/.git/config", "/.svn/entries", "/.DS_Store",
        ]
        for path in debug_paths:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200 and len(resp.text) > 50:
                    findings.append({
                        "type": "debug_endpoint",
                        "path": path,
                        "size": len(resp.text),
                        "detail": f"Debug/diagnostic endpoint exposed: {path}",
                        "severity": "high",
                    })
                    raw_lines.append(f"  HIGH: Debug endpoint {path} ({len(resp.text)} bytes)")
            except Exception:
                continue

        # Phase 5: Information disclosure in headers
        raw_lines.append("\n[Phase 5: Header Information Disclosure]")
        try:
            resp = self.session.get(base_url, timeout=10)
            for header in PRIV_HEADERS:
                value = resp.headers.get(header)
                if value:
                    findings.append({
                        "type": "info_disclosure_header",
                        "header": header,
                        "value": value,
                        "detail": f"Info disclosure: {header}: {value}",
                        "severity": "low",
                    })
                    raw_lines.append(f"  LOW: {header}: {value}")
        except Exception:
            pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "33_privesc.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("PrivEsc scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
