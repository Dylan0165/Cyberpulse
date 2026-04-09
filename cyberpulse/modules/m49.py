"""Module 49 — IPv6 Security Testing.

Tests IPv6 configuration, dual-stack issues, and IPv6-specific
security vulnerabilities and misconfigurations.
"""

import json
import logging
import re
import socket
import subprocess
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m49")

# IPv6-specific ports to scan
IPV6_PORTS = [22, 80, 443, 8080, 8443, 25, 53, 110, 143]


class Scanner:
    name = "IPv6 Security Testing"
    phase = "scanning"
    description = "Tests IPv6 configuration, dual-stack issues, and IPv6-specific vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"IPv6 security testing for {self.target}"]

        # Phase 1: IPv6 (AAAA) record detection
        raw_lines.append("\n[Phase 1: IPv6 Record Detection]")
        ipv6_addr = self._get_ipv6()
        if ipv6_addr:
            findings.append({
                "type": "ipv6_enabled",
                "address": ipv6_addr,
                "detail": f"IPv6 enabled: {ipv6_addr}",
                "severity": "info",
            })
            raw_lines.append(f"  IPv6 address: {ipv6_addr}")
        else:
            findings.append({
                "type": "ipv6_not_enabled",
                "detail": "No AAAA record — IPv6 not configured",
                "severity": "info",
            })
            raw_lines.append("  No AAAA record (IPv6 not configured)")
            # Not much more to test without IPv6
            raw_output = "\n".join(raw_lines)
            outfile = self.output_dir / "49_ipv6.json"
            with open(outfile, "w", encoding="utf-8") as f:
                json.dump({"findings": findings}, f, indent=2)
            return {"findings": findings, "raw_output": raw_output}

        # Phase 2: Dual-stack consistency check
        raw_lines.append("\n[Phase 2: Dual-Stack Consistency]")
        ipv4_addr = self._get_ipv4()
        if ipv4_addr:
            raw_lines.append(f"  IPv4: {ipv4_addr}")
            raw_lines.append(f"  IPv6: {ipv6_addr}")

            # Compare HTTP responses on both stacks
            try:
                resp_v4 = requests.get(f"http://{self.target}",
                                       timeout=10, verify=False)
                resp_v6 = requests.get(f"http://[{ipv6_addr}]/",
                                       headers={"Host": self.target},
                                       timeout=10, verify=False)
                if resp_v4.status_code != resp_v6.status_code:
                    findings.append({
                        "type": "dual_stack_inconsistent",
                        "ipv4_status": resp_v4.status_code,
                        "ipv6_status": resp_v6.status_code,
                        "detail": f"Dual-stack inconsistency: v4={resp_v4.status_code}, v6={resp_v6.status_code}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: Inconsistent: v4={resp_v4.status_code} vs v6={resp_v6.status_code}")
                else:
                    raw_lines.append("  OK: Responses consistent between IPv4 and IPv6")
            except Exception as e:
                raw_lines.append(f"  Dual-stack comparison error: {e}")

        # Phase 3: IPv6 port scan
        raw_lines.append("\n[Phase 3: IPv6 Port Scan]")
        for port in IPV6_PORTS:
            try:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((ipv6_addr, port, 0, 0))
                if result == 0:
                    findings.append({
                        "type": "ipv6_open_port",
                        "port": port,
                        "address": ipv6_addr,
                        "detail": f"IPv6 port {port} open on {ipv6_addr}",
                        "severity": "info",
                    })
                    raw_lines.append(f"  Port {port} open on IPv6")
                sock.close()
            except Exception:
                continue

        # Phase 4: IPv6-only services (not on IPv4)
        raw_lines.append("\n[Phase 4: IPv6-only Services]")
        ipv4_ports = set()
        if ipv4_addr:
            for port in IPV6_PORTS:
                try:
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    if sock.connect_ex((ipv4_addr, port)) == 0:
                        ipv4_ports.add(port)
                    sock.close()
                except Exception:
                    continue

        ipv6_only_ports = []
        for port in IPV6_PORTS:
            try:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.settimeout(2)
                if sock.connect_ex((ipv6_addr, port, 0, 0)) == 0:
                    if port not in ipv4_ports:
                        ipv6_only_ports.append(port)
                sock.close()
            except Exception:
                continue

        if ipv6_only_ports:
            findings.append({
                "type": "ipv6_only_services",
                "ports": ipv6_only_ports,
                "detail": f"IPv6-only services on ports: {ipv6_only_ports} — may bypass IPv4 firewall!",
                "severity": "high",
            })
            raw_lines.append(f"  HIGH: IPv6-only services: {ipv6_only_ports}")
        else:
            raw_lines.append("  No IPv6-only services detected")

        # Phase 5: IPv6 security headers
        raw_lines.append("\n[Phase 5: IPv6 HTTP Security Headers]")
        try:
            resp = requests.get(f"http://[{ipv6_addr}]/",
                                headers={"Host": self.target},
                                timeout=10, verify=False)
            security_headers = ["x-content-type-options", "x-frame-options",
                                "strict-transport-security", "content-security-policy"]
            resp_headers = {h.lower() for h in resp.headers}
            missing = [h for h in security_headers if h not in resp_headers]
            if missing:
                findings.append({
                    "type": "ipv6_missing_headers",
                    "missing": missing,
                    "detail": f"IPv6 endpoint missing security headers: {', '.join(missing)}",
                    "severity": "medium",
                })
                raw_lines.append(f"  MEDIUM: Missing on IPv6: {', '.join(missing)}")
            else:
                raw_lines.append("  OK: Security headers present on IPv6")
        except Exception:
            raw_lines.append("  Could not test IPv6 HTTP headers")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "49_ipv6.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("IPv6 scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_ipv6(self) -> str | None:
        """Resolve AAAA record."""
        try:
            result = subprocess.run(
                ["nslookup", "-type=AAAA", self.target],
                capture_output=True, text=True, timeout=10,
            )
            matches = re.findall(r"(?:Address:|address\s*=)\s*([0-9a-fA-F:]+)",
                                 result.stdout)
            # Filter out DNS server addresses
            for addr in matches:
                if ":" in addr and not addr.startswith("::1"):
                    return addr
        except Exception:
            pass
        try:
            infos = socket.getaddrinfo(self.target, None, socket.AF_INET6)
            if infos:
                return infos[0][4][0]
        except Exception:
            pass
        return None

    def _get_ipv4(self) -> str | None:
        try:
            return socket.gethostbyname(self.target)
        except Exception:
            return None
