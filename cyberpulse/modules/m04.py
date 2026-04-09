"""Module 04 — Subdomain Discovery.

Discovers subdomains using certificate transparency logs, DNS brute force,
and public sources.
"""

import json
import logging
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m04")

# Common subdomains to brute-force
COMMON_SUBS = [
    "www", "mail", "ftp", "smtp", "pop", "imap", "webmail", "admin",
    "portal", "vpn", "ns1", "ns2", "dns", "mx", "api", "dev", "staging",
    "test", "beta", "blog", "shop", "store", "app", "cdn", "media",
    "static", "assets", "img", "images", "m", "mobile", "login", "auth",
    "sso", "dashboard", "panel", "cpanel", "whm", "plesk", "gitlab",
    "jenkins", "ci", "jira", "confluence", "wiki", "docs", "status",
    "monitor", "grafana", "prometheus", "kibana", "elastic", "db",
    "mysql", "postgres", "redis", "mongo", "mq", "rabbitmq", "kafka",
    "s3", "backup", "old", "new", "v2", "internal", "intranet", "remote",
    "gateway", "proxy", "lb", "loadbalancer", "firewall", "exchange",
    "owa", "autodiscover", "office", "teams", "sharepoint",
]


class Scanner:
    name = "Subdomain Discovery"
    phase = "reconnaissance"
    description = "Discovers subdomains via CT logs and DNS brute-force"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Subdomain discovery for {self.target}"]
        discovered = set()

        # Method 1: Certificate Transparency via crt.sh
        raw_lines.append("\n[crt.sh]")
        ct_subs = self._query_crtsh()
        for sub in ct_subs:
            if sub not in discovered:
                discovered.add(sub)
                raw_lines.append(f"  {sub}")

        # Method 2: DNS brute force
        raw_lines.append(f"\n[DNS brute force — {len(COMMON_SUBS)} candidates]")
        for prefix in COMMON_SUBS:
            fqdn = f"{prefix}.{self.target}"
            try:
                ip = socket.gethostbyname(fqdn)
                if fqdn not in discovered:
                    discovered.add(fqdn)
                    raw_lines.append(f"  {fqdn} -> {ip}")
            except socket.gaierror:
                pass

        # Build findings
        for sub in sorted(discovered):
            ip = ""
            try:
                ip = socket.gethostbyname(sub)
            except Exception:
                pass

            findings.append({
                "type": "subdomain",
                "subdomain": sub,
                "ip": ip,
                "severity": "info",
            })

            # Flag interesting subdomains
            lower = sub.lower()
            for keyword in ["admin", "internal", "staging", "test", "dev", "jenkins", "gitlab", "backup", "old"]:
                if keyword in lower:
                    findings.append({
                        "type": "interesting_subdomain",
                        "subdomain": sub,
                        "reason": f"Contains '{keyword}' — may expose sensitive resources",
                        "severity": "medium",
                    })
                    break

        raw_lines.append(f"\nTotal unique subdomains: {len(discovered)}")
        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "04_subdomains.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "subdomains": sorted(discovered)}, f, indent=2)

        logger.info("Subdomain discovery %s: %d subdomains found", self.target, len(discovered))
        return {"findings": findings, "raw_output": raw_output}

    def _query_crtsh(self) -> list[str]:
        """Query crt.sh for certificate transparency data."""
        subs = set()
        try:
            resp = requests.get(
                f"https://crt.sh/?q=%.{self.target}&output=json",
                timeout=15,
                headers={"User-Agent": "CyberPulse/1.0"},
            )
            if resp.status_code == 200:
                for entry in resp.json():
                    name = entry.get("name_value", "")
                    for part in name.split("\n"):
                        part = part.strip().lower()
                        if part.endswith(self.target.lower()) and "*" not in part:
                            subs.add(part)
        except Exception as e:
            logger.warning("crt.sh query failed: %s", e)
        return sorted(subs)
