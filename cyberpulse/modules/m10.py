"""Module 10 — Vulnerability Scanner (CVE-based).

Checks detected technologies and versions against known CVEs using
local scraped data and NVD patterns.
"""

import json
import logging
import re
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m10")


class Scanner:
    name = "CVE Vulnerability Check"
    phase = "vulnerability_scan"
    description = "Matches detected service versions against known CVE vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"CVE vulnerability check for {self.target}"]

        # Load data from previous modules
        technologies = self._load_technologies()
        services = self._load_services()
        all_components = technologies + services
        raw_lines.append(f"Loaded {len(all_components)} components to check")

        # Load local CVE data
        from config import Config
        cve_file = Config.DATA_DIR / "scraped" / "cve_feed.json"
        known_cves = []
        if cve_file.exists():
            with open(cve_file, "r", encoding="utf-8") as f:
                known_cves = json.load(f)
            raw_lines.append(f"Loaded {len(known_cves)} CVEs from local feed")
        else:
            raw_lines.append("No local CVE data — using built-in patterns only")

        # Built-in vulnerability patterns (product, version_regex, cve, severity, description)
        builtin_vulns = [
            ("apache", r"2\.[24]\.\d+", "CVE-2021-41773", "critical", "Apache 2.4.49/50 path traversal"),
            ("apache", r"2\.4\.(49|50)", "CVE-2021-42013", "critical", "Apache 2.4.49/50 RCE via path traversal"),
            ("nginx", r"1\.(1[0-9]|[0-9])\.", "CVE-2021-23017", "high", "Nginx DNS resolver vulnerability"),
            ("openssl", r"1\.0\.", "CVE-2014-0160", "critical", "OpenSSL Heartbleed"),
            ("openssl", r"1\.0\.[01]", "CVE-2014-3566", "medium", "POODLE attack on SSLv3"),
            ("php", r"[57]\.\d+\.\d+", "CVE-2019-11043", "critical", "PHP-FPM RCE"),
            ("php", r"5\.", "deprecated", "high", "PHP 5.x is end-of-life"),
            ("jquery", r"[12]\.", "CVE-2020-11022", "medium", "jQuery < 3.5.0 XSS via HTML injection"),
            ("wordpress", r"[0-5]\.\d+", "multiple", "high", "WordPress < 6.0 has multiple known vulnerabilities"),
            ("drupal", r"[0-8]\.", "SA-CORE-2018-002", "critical", "Drupalgeddon2 RCE"),
            ("vsftpd", r"2\.3\.4", "CVE-2011-2523", "critical", "vsftpd 2.3.4 backdoor"),
            ("microsoft-iis", r"[67]\.", "multiple", "high", "IIS 6/7 has multiple known vulnerabilities"),
            ("redis", r"[0-5]\.", "CVE-2022-0543", "critical", "Redis < 6.0 sandbox escape"),
            ("elasticsearch", r"[1-6]\.", "CVE-2015-1427", "critical", "Elasticsearch < 7 Groovy sandbox bypass"),
            ("mongodb", r"[0-3]\.", "CVE-2017-2665", "high", "MongoDB < 4.0 auth bypass"),
        ]

        # Match against built-in patterns
        raw_lines.append("\n[Built-in Pattern Matching]")
        for component in all_components:
            product = component.get("product", "").lower()
            version = component.get("version", "")
            if not product or not version:
                continue

            for vuln_product, ver_regex, cve_id, severity, description in builtin_vulns:
                if vuln_product in product and re.match(ver_regex, version):
                    raw_lines.append(f"  [!] {product} v{version}: {cve_id} — {description}")
                    findings.append({
                        "type": "known_vulnerability",
                        "product": product,
                        "version": version,
                        "cve": cve_id,
                        "description": description,
                        "severity": severity,
                    })

        # Match against local CVE feed
        if known_cves:
            raw_lines.append("\n[Local CVE Feed Matching]")
            for component in all_components:
                product = component.get("product", "").lower()
                version = component.get("version", "")
                if not product:
                    continue

                for cve in known_cves:
                    cve_products = [p.lower() for p in cve.get("affected_products", [])]
                    if any(product in cp or cp in product for cp in cve_products):
                        # Check if version is in affected range
                        affected_versions = cve.get("affected_versions", "")
                        if version and affected_versions and version in affected_versions:
                            raw_lines.append(f"  [!] {cve['cve_id']}: {cve.get('summary', '')[:80]}")
                            findings.append({
                                "type": "known_vulnerability",
                                "product": product,
                                "version": version,
                                "cve": cve["cve_id"],
                                "description": cve.get("summary", ""),
                                "severity": cve.get("severity", "medium"),
                                "source": "local_cve_feed",
                            })

        if not findings:
            raw_lines.append("\nNo known vulnerabilities matched")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "10_cve_check.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("CVE check %s: %d vulnerabilities matched", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _load_technologies(self) -> list[dict]:
        """Load detected technologies from module 05."""
        tech_file = self.output_dir / "05_technology.json"
        if tech_file.exists():
            with open(tech_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                techs = data.get("technologies", [])
                return [{"product": t.get("technology", ""), "version": t.get("version", "")} for t in techs]
        return []

    def _load_services(self) -> list[dict]:
        """Load service info from modules 01 and 02."""
        components = []
        for fname in ("01_port_scan.json", "02_fingerprint.json"):
            fpath = self.output_dir / fname
            if fpath.exists():
                with open(fpath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for finding in data.get("findings", []):
                        product = finding.get("product", "") or finding.get("service", "")
                        version = finding.get("version", "")
                        if product:
                            components.append({"product": product, "version": version})
        return components
