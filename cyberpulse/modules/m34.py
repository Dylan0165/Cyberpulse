"""Module 34 — Lateral Movement Discovery.

Maps the internal network surface reachable from the target: detects
internal services, shared host resources, and potential pivot points.
"""

import json
import logging
import re
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m34")

INTERNAL_RANGES = [
    ("10.0.0.", 1, 5),
    ("172.16.0.", 1, 5),
    ("192.168.0.", 1, 5),
    ("192.168.1.", 1, 5),
]

COMMON_PORTS = [22, 80, 443, 3306, 5432, 6379, 8080, 8443, 27017, 9200]


class Scanner:
    name = "Lateral Movement Discovery"
    phase = "exploitation"
    description = "Maps internal services and potential pivot points from the target"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Lateral movement discovery for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Reverse DNS and additional hostnames
        raw_lines.append("\n[Phase 1: Reverse DNS / Additional Hosts]")
        try:
            ip = socket.gethostbyname(self.target)
            raw_lines.append(f"  Target resolves to {ip}")
            try:
                hostname, aliases, _ = socket.gethostbyaddr(ip)
                all_names = [hostname] + aliases
                for name in all_names:
                    findings.append({
                        "type": "reverse_dns",
                        "ip": ip,
                        "hostname": name,
                        "detail": f"Reverse DNS: {ip} → {name}",
                        "severity": "info",
                    })
                    raw_lines.append(f"  Reverse DNS: {ip} → {name}")
            except Exception:
                raw_lines.append("  No reverse DNS")
        except Exception:
            raw_lines.append("  DNS resolution failed")

        # Phase 2: Virtual host enumeration
        raw_lines.append("\n[Phase 2: Virtual Host Enumeration]")
        vhost_prefixes = [
            "dev", "staging", "test", "internal", "api", "admin",
            "portal", "intranet", "mail", "vpn", "git", "ci", "cd",
            "jenkins", "grafana", "prometheus", "kibana",
        ]
        domain_parts = self.target.split(".")
        if len(domain_parts) >= 2:
            base_domain = ".".join(domain_parts[-2:])
            for prefix in vhost_prefixes:
                vhost = f"{prefix}.{base_domain}"
                try:
                    resp = self.session.get(
                        base_url,
                        headers={"Host": vhost},
                        timeout=5,
                        allow_redirects=False,
                    )
                    if resp.status_code in (200, 301, 302, 403):
                        # Compare with normal response to detect differing content
                        normal = self.session.get(base_url, timeout=5)
                        if resp.text != normal.text or resp.status_code != normal.status_code:
                            findings.append({
                                "type": "vhost",
                                "vhost": vhost,
                                "status": resp.status_code,
                                "detail": f"Virtual host responds: {vhost} (HTTP {resp.status_code})",
                                "severity": "medium",
                            })
                            raw_lines.append(f"  MEDIUM: VHost {vhost} — HTTP {resp.status_code}")
                except Exception:
                    continue

        # Phase 3: SSRF-based internal service discovery
        raw_lines.append("\n[Phase 3: SSRF-based Internal Probing]")
        ssrf_test_urls = [
            "http://127.0.0.1",
            "http://localhost",
            "http://169.254.169.254/latest/meta-data/",
            "http://10.0.0.1",
            "http://192.168.1.1",
        ]
        ssrf_params = ["url", "target", "host", "redirect", "fetch", "proxy"]
        for param in ssrf_params:
            for internal_url in ssrf_test_urls:
                url = f"{base_url}/?{param}={internal_url}"
                try:
                    resp = self.session.get(url, timeout=8)
                    if resp.status_code == 200 and len(resp.text) > 100:
                        internal_indicators = [
                            "ami-id", "instance-id", "local-ipv4",
                            "Apache", "nginx", "IIS",
                            "phpinfo", "root:",
                        ]
                        if any(ind in resp.text for ind in internal_indicators):
                            findings.append({
                                "type": "ssrf_internal",
                                "parameter": param,
                                "internal_url": internal_url,
                                "detail": f"SSRF: internal service reachable via '{param}' → {internal_url}",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: SSRF {param} → {internal_url}")
                            break
                except Exception:
                    continue

        # Phase 4: Network service detection on common ports
        raw_lines.append("\n[Phase 4: Service Detection on Target]")
        try:
            target_ip = socket.gethostbyname(self.target)
            for port in COMMON_PORTS:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((target_ip, port))
                if result == 0:
                    service = self._banner_grab(target_ip, port)
                    findings.append({
                        "type": "open_port",
                        "ip": target_ip,
                        "port": port,
                        "service": service,
                        "detail": f"Open port: {target_ip}:{port} ({service})",
                        "severity": "info",
                    })
                    raw_lines.append(f"  Port {port} open: {service}")
                sock.close()
        except Exception:
            raw_lines.append("  Port scan failed")

        # Phase 5: Shared hosting / related sites
        raw_lines.append("\n[Phase 5: Shared Hosting Detection]")
        shared_indicators = [
            "/cpanel", "/whm", "/plesk", "/.well-known/",
        ]
        for path in shared_indicators:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8, allow_redirects=False)
                if resp.status_code in (200, 301, 302):
                    findings.append({
                        "type": "shared_hosting",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"Shared hosting indicator: {path}",
                        "severity": "info",
                    })
                    raw_lines.append(f"  INFO: {path} — HTTP {resp.status_code}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "34_lateral.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Lateral movement scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _banner_grab(self, ip: str, port: int) -> str:
        known = {22: "SSH", 80: "HTTP", 443: "HTTPS", 3306: "MySQL",
                 5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
                 8443: "HTTPS-Alt", 27017: "MongoDB", 9200: "Elasticsearch"}
        service = known.get(port, "unknown")
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect((ip, port))
            banner = sock.recv(1024).decode(errors="ignore").strip()
            sock.close()
            if banner:
                return f"{service} — {banner[:100]}"
        except Exception:
            pass
        return service

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
