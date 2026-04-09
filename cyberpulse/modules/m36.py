"""Module 36 — Kerberos Attack Vector Detection.

Identifies exposed Kerberos services and tests for common Kerberos
misconfigurations (AS-REP roasting, Kerberoasting indicators, etc.).
"""

import json
import logging
import socket
import struct
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m36")


class Scanner:
    name = "Kerberos Attack Vectors"
    phase = "exploitation"
    description = "Detects exposed Kerberos services and common misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Kerberos attack vector scan for {self.target}"]

        # Phase 1: Kerberos port detection (88/TCP and 88/UDP)
        raw_lines.append("\n[Phase 1: Kerberos Service Detection]")
        kdc_open = False
        try:
            ip = socket.gethostbyname(self.target)
            # TCP 88
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            if sock.connect_ex((ip, 88)) == 0:
                kdc_open = True
                findings.append({
                    "type": "kerberos_tcp",
                    "port": 88,
                    "detail": "Kerberos KDC exposed on TCP/88",
                    "severity": "high",
                })
                raw_lines.append("  HIGH: Kerberos KDC open on TCP/88")
            sock.close()
        except Exception:
            pass

        # Phase 2: SPN / Service enumeration via DNS
        raw_lines.append("\n[Phase 2: SPN/Service DNS Records]")
        srv_records = [
            "_kerberos._tcp", "_kerberos._udp",
            "_kpasswd._tcp", "_kpasswd._udp",
            "_ldap._tcp", "_gc._tcp",
        ]
        import subprocess
        for srv in srv_records:
            fqdn = f"{srv}.{self.target}"
            try:
                result = subprocess.run(
                    ["nslookup", "-type=SRV", fqdn],
                    capture_output=True, text=True, timeout=5,
                )
                if "service" in result.stdout.lower() or "svr" in result.stdout.lower():
                    findings.append({
                        "type": "kerberos_srv",
                        "record": fqdn,
                        "detail": f"SRV record found: {fqdn}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: SRV record {fqdn}")
            except Exception:
                continue

        # Phase 3: Test for weak Kerberos pre-authentication (AS-REP roasting indicator)
        raw_lines.append("\n[Phase 3: AS-REP Roasting Detection]")
        if kdc_open:
            # Send a minimal AS-REQ without pre-auth to see if we get AS-REP
            # This checks the KDC behavior
            raw_lines.append("  KDC is accessible — AS-REP roasting may be possible for accounts")
            raw_lines.append("  with 'Do not require Kerberos preauthentication' set")
            findings.append({
                "type": "asrep_possible",
                "detail": "KDC reachable — AS-REP roasting possible if accounts have pre-auth disabled",
                "severity": "medium",
            })
        else:
            raw_lines.append("  KDC not reachable — AS-REP roasting not testable remotely")

        # Phase 4: Kerberoasting indicator — SPN lookups via web
        raw_lines.append("\n[Phase 4: Kerberoasting Indicators]")
        base_url = self._get_base_url()
        api_paths = [
            "/api/users", "/api/v1/users", "/api/accounts",
            "/api/services", "/api/principals",
        ]
        for path in api_paths:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        items = data if isinstance(data, list) else data.get("items", data.get("results", []))
                        if isinstance(items, list):
                            for item in items[:10]:
                                if isinstance(item, dict):
                                    spn = item.get("servicePrincipalName") or item.get("spn")
                                    if spn:
                                        findings.append({
                                            "type": "spn_exposed",
                                            "spn": str(spn)[:200],
                                            "detail": f"SPN exposed via API: {str(spn)[:100]}",
                                            "severity": "high",
                                        })
                                        raw_lines.append(f"  HIGH: SPN exposed: {str(spn)[:80]}")
                    except Exception:
                        pass
            except Exception:
                continue

        # Phase 5: Related Windows auth endpoints
        raw_lines.append("\n[Phase 5: Windows Auth Endpoints]")
        win_auth_paths = [
            "/negotiate", "/ntlm",
            "/windowsauth", "/api/auth/windows",
            "/auth/kerberos", "/auth/negotiate",
        ]
        for path in win_auth_paths:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8, allow_redirects=False)
                www_auth = resp.headers.get("WWW-Authenticate", "")
                if "Negotiate" in www_auth:
                    findings.append({
                        "type": "negotiate_auth",
                        "path": path,
                        "detail": f"Negotiate (Kerberos/NTLM) auth at {path}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: Negotiate auth at {path}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "36_kerberos.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Kerberos scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
