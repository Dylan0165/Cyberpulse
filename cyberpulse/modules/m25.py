"""Module 25 — Default Credentials Checker.

Tests common services for default/factory credentials.
Only tests credentials against services already identified as open.
"""

import json
import logging
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m25")

# Default creds per service (service_name -> [(user, pass), ...])
DEFAULT_CREDS = {
    "ssh": [
        ("admin", "admin"), ("root", "root"), ("root", "toor"),
        ("admin", "password"), ("admin", "1234"), ("root", "password"),
        ("pi", "raspberry"), ("ubnt", "ubnt"), ("admin", ""),
    ],
    "ftp": [
        ("anonymous", ""), ("anonymous", "anonymous@"), ("admin", "admin"),
        ("ftp", "ftp"), ("admin", "password"), ("root", "root"),
    ],
    "mysql": [
        ("root", ""), ("root", "root"), ("root", "mysql"), ("root", "password"),
        ("admin", "admin"), ("dbadmin", "dbadmin"),
    ],
    "postgres": [
        ("postgres", "postgres"), ("postgres", "password"), ("admin", "admin"),
    ],
    "redis": [
        ("", ""),  # Redis often has no auth
    ],
    "mongodb": [
        ("admin", "admin"), ("root", "root"), ("", ""),  # No auth
    ],
    "telnet": [
        ("admin", "admin"), ("admin", "password"), ("root", "root"),
        ("admin", "1234"), ("user", "user"),
    ],
    "snmp": [
        ("public", ""), ("private", ""), ("community", ""),
    ],
}

# Web login forms: common admin panel default creds
WEB_DEFAULT_CREDS = [
    ("admin", "admin"), ("admin", "password"), ("admin", "admin123"),
    ("admin", "12345"), ("administrator", "administrator"),
    ("admin", "changeme"), ("root", "root"), ("admin", ""),
    ("user", "user"), ("test", "test"), ("guest", "guest"),
]

# Common admin panel paths
ADMIN_PATHS = [
    "/admin", "/admin/login", "/administrator", "/wp-admin",
    "/wp-login.php", "/login", "/admin.php", "/user/login",
    "/panel", "/manage", "/dashboard/login", "/cpanel",
    "/phpmyadmin", "/adminer", "/webmin",
]


class Scanner:
    name = "Default Credentials"
    phase = "exploitation"
    description = "Tests services and admin panels for default/factory credentials"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Default credentials check for {self.target}"]

        # Phase 1: Check network services
        raw_lines.append("\n[Phase 1: Network Service Credentials]")

        # Read port scan results if available
        port_file = self.output_dir / "01_port_scan.json"
        open_services = []
        if port_file.exists():
            try:
                data = json.loads(port_file.read_text())
                for f in data.get("findings", []):
                    svc = f.get("service", "").lower()
                    port = f.get("port", 0)
                    if svc or port:
                        open_services.append((svc, port))
            except Exception:
                pass

        # Test SSH
        if any(s == "ssh" or p == 22 for s, p in open_services):
            raw_lines.append("  [SSH on port 22]")
            ssh_findings = self._test_ssh_creds()
            findings.extend(ssh_findings)
            for f in ssh_findings:
                raw_lines.append(f"    {f['detail']}")

        # Test FTP
        if any(s == "ftp" or p == 21 for s, p in open_services):
            raw_lines.append("  [FTP on port 21]")
            ftp_findings = self._test_ftp_creds()
            findings.extend(ftp_findings)
            for f in ftp_findings:
                raw_lines.append(f"    {f['detail']}")

        # Test Redis (no auth check)
        if any(s == "redis" or p == 6379 for s, p in open_services):
            raw_lines.append("  [Redis on port 6379]")
            redis_f = self._test_redis_noauth()
            if redis_f:
                findings.append(redis_f)
                raw_lines.append(f"    {redis_f['detail']}")

        # Test MongoDB
        if any(s in ("mongodb", "mongo") or p == 27017 for s, p in open_services):
            raw_lines.append("  [MongoDB on port 27017]")
            mongo_f = self._test_mongo_noauth()
            if mongo_f:
                findings.append(mongo_f)
                raw_lines.append(f"    {mongo_f['detail']}")

        # Phase 2: Web admin panels
        raw_lines.append("\n[Phase 2: Web Admin Panel Credentials]")
        base_url = self._get_base_url()

        for path in ADMIN_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=True)
                if resp.status_code == 200 and self._looks_like_login(resp.text):
                    raw_lines.append(f"\n  Found login at {path}")
                    findings.append({
                        "type": "admin_panel_found",
                        "path": path,
                        "detail": f"Admin panel / login form found at {path}",
                        "severity": "info",
                    })

                    # Test default creds on the form
                    form_vuln = self._test_web_login(url, resp.text)
                    if form_vuln:
                        findings.append(form_vuln)
                        raw_lines.append(f"    CRITICAL: {form_vuln['detail']}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "25_default_creds.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Default creds check %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _test_ssh_creds(self) -> list:
        findings = []
        try:
            import paramiko
            for user, pwd in DEFAULT_CREDS.get("ssh", []):
                try:
                    client = paramiko.SSHClient()
                    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                    client.connect(self.target, port=22, username=user,
                                   password=pwd, timeout=5, auth_timeout=5,
                                   allow_agent=False, look_for_keys=False)
                    client.close()
                    findings.append({
                        "type": "default_cred_ssh",
                        "service": "SSH",
                        "username": user,
                        "detail": f"SSH login successful with {user}:{pwd}",
                        "severity": "critical",
                    })
                    break  # Stop after first success
                except Exception:
                    continue
        except ImportError:
            pass
        return findings

    def _test_ftp_creds(self) -> list:
        findings = []
        import ftplib
        for user, pwd in DEFAULT_CREDS.get("ftp", []):
            try:
                ftp = ftplib.FTP()
                ftp.connect(self.target, 21, timeout=5)
                ftp.login(user, pwd)
                ftp.quit()
                findings.append({
                    "type": "default_cred_ftp",
                    "service": "FTP",
                    "username": user,
                    "detail": f"FTP login successful with {user}:{pwd or '(empty)'}",
                    "severity": "critical" if user != "anonymous" else "medium",
                })
                break
            except Exception:
                continue
        return findings

    def _test_redis_noauth(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.target, 6379))
            s.sendall(b"PING\r\n")
            resp = s.recv(1024).decode("utf-8", errors="replace")
            s.close()
            if "+PONG" in resp:
                return {
                    "type": "redis_noauth",
                    "service": "Redis",
                    "detail": "Redis accessible without authentication!",
                    "severity": "critical",
                }
        except Exception:
            pass
        return None

    def _test_mongo_noauth(self):
        try:
            # Try HTTP interface
            resp = self.session.get(f"http://{self.target}:27017", timeout=5)
            if "mongodb" in resp.text.lower() or "It looks like" in resp.text:
                return {
                    "type": "mongodb_exposed",
                    "service": "MongoDB",
                    "detail": "MongoDB HTTP interface exposed without authentication!",
                    "severity": "critical",
                }
        except Exception:
            pass
        return None

    def _looks_like_login(self, html: str) -> bool:
        html_lower = html.lower()
        return ("password" in html_lower and
                ("<form" in html_lower or "<input" in html_lower))

    def _test_web_login(self, url: str, html: str):
        """Very basic form-based default credential test."""
        import re
        # Find form action
        action_match = re.search(r'<form[^>]*action=["\']([^"\']*)["\']', html, re.I)
        action = action_match.group(1) if action_match else url

        if action.startswith("/"):
            action = self._get_base_url() + action

        # Find input field names
        inputs = re.findall(r'<input[^>]*name=["\']([^"\']*)["\']', html, re.I)
        user_field = None
        pass_field = None
        for inp in inputs:
            il = inp.lower()
            if any(k in il for k in ("user", "login", "email", "name")):
                user_field = inp
            if any(k in il for k in ("pass", "pwd")):
                pass_field = inp

        if not user_field or not pass_field:
            return None

        for user, pwd in WEB_DEFAULT_CREDS[:5]:  # Limit attempts
            try:
                resp = self.session.post(action, data={
                    user_field: user, pass_field: pwd
                }, timeout=10, allow_redirects=True)

                # Detect successful login
                body = resp.text.lower()
                if resp.status_code == 200 and not self._looks_like_login(body):
                    if any(kw in body for kw in ("dashboard", "welcome", "logout", "profile")):
                        return {
                            "type": "default_cred_web",
                            "service": "Web Admin",
                            "username": user,
                            "url": url,
                            "detail": f"Web login successful with {user}:{pwd} at {url}",
                            "severity": "critical",
                        }
            except Exception:
                continue
        return None

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
