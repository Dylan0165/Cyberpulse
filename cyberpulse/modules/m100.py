"""Module 100 — Shodan API Intelligence.

Queries Shodan API for publicly exposed services, vulnerabilities, and intelligence.
"""

import json
import logging
import re
import socket
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m100")


class Scanner:
    name = "Shodan API Intelligence"
    phase = "reconnaissance"
    description = "Queries Shodan for exposed services and known vulnerabilities"
    target_types = ["web", "network", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.api_key = config.get("SHODAN_API_KEY", "")

    def _extract_host(self, target: str) -> str:
        target = target.strip()
        if "://" in target:
            target = target.split("://", 1)[1]
        return target.split("/")[0].split(":")[0]

    def _resolve_ip(self, host: str) -> str:
        """Resolve hostname to IP address."""
        try:
            return socket.gethostbyname(host)
        except socket.gaierror:
            return ""

    def run(self) -> dict:
        if not self.api_key:
            return {
                "findings": [],
                "raw_output": "Shodan API key niet geconfigureerd (SHODAN_API_KEY)",
                "error": None,
            }

        findings = []
        raw_lines = []
        host = self._extract_host(self.target)
        ip = self._resolve_ip(host)

        if not ip:
            return {
                "findings": [],
                "raw_output": f"Kon {host} niet resolven naar IP adres",
                "error": "DNS resolution failed",
            }

        raw_lines.append(f"Target: {host} -> {ip}")

        # Query Shodan host API
        f, o = self._query_host(ip)
        findings.extend(f)
        raw_lines.append(o)

        # Save results
        if findings:
            result_file = self.output_dir / "m100_shodan.json"
            result_file.write_text(
                json.dumps({"ip": ip, "host": host, "findings": findings}, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _query_host(self, ip: str) -> tuple:
        """Query Shodan /shodan/host/{ip} endpoint."""
        findings = []
        raw_lines = []

        try:
            import urllib.request
            import urllib.error
            import ssl

            url = f"https://api.shodan.io/shodan/host/{ip}?key={self.api_key}"
            ctx = ssl.create_default_context()
            req = urllib.request.Request(url, headers={"User-Agent": "CyberPulse/2.0"})
            resp = urllib.request.urlopen(req, timeout=30, context=ctx)
            data = json.loads(resp.read().decode("utf-8"))

            # General info
            org = data.get("org", "")
            os_name = data.get("os", "")
            ports = data.get("ports", [])
            raw_lines.append(f"Organization: {org}")
            raw_lines.append(f"OS: {os_name}")
            raw_lines.append(f"Open ports: {ports}")

            # Check vulnerabilities
            vulns = data.get("vulns", [])
            for vuln in vulns:
                severity = "critical" if vuln.startswith("CVE-") else "high"
                findings.append({
                    "type": "shodan_vuln",
                    "severity": severity,
                    "detail": f"Shodan meldt bekende kwetsbaarheid: {vuln}",
                    "cve": vuln,
                    "ip": ip,
                })

            # Analyze services/banners
            services = data.get("data", [])
            for service in services:
                port = service.get("port", 0)
                product = service.get("product", "")
                version = service.get("version", "")
                transport = service.get("transport", "tcp")

                raw_lines.append(f"  Port {port}/{transport}: {product} {version}")

                # Check for dangerous services exposed to internet
                dangerous_ports = {
                    21: "FTP", 23: "Telnet", 445: "SMB", 3306: "MySQL",
                    5432: "PostgreSQL", 6379: "Redis", 27017: "MongoDB",
                    9200: "Elasticsearch", 11211: "Memcached",
                }

                if port in dangerous_ports:
                    findings.append({
                        "type": "exposed_service",
                        "severity": "high",
                        "detail": (
                            f"Gevaarlijke service publiek bereikbaar: "
                            f"{dangerous_ports[port]} op poort {port}"
                        ),
                        "port": port,
                        "service": dangerous_ports[port],
                        "ip": ip,
                    })

                # Check for service-specific vulns
                service_vulns = service.get("vulns", {})
                for cve_id, vuln_info in service_vulns.items():
                    cvss = vuln_info.get("cvss", 0) if isinstance(vuln_info, dict) else 0
                    if cvss >= 9.0:
                        sev = "critical"
                    elif cvss >= 7.0:
                        sev = "high"
                    elif cvss >= 4.0:
                        sev = "medium"
                    else:
                        sev = "low"

                    findings.append({
                        "type": "shodan_service_vuln",
                        "severity": sev,
                        "detail": f"{cve_id} (CVSS {cvss}) op poort {port} ({product})",
                        "cve": cve_id,
                        "cvss": cvss,
                        "port": port,
                        "ip": ip,
                    })

            return findings, "\n".join(raw_lines)

        except urllib.error.HTTPError as e:
            if e.code == 404:
                return findings, f"Shodan: geen informatie voor {ip}"
            return findings, f"Shodan API fout: HTTP {e.code}"
        except Exception as e:
            return findings, f"Shodan query fout: {e}"
