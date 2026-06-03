"""Module 10-CVE — CVE Correlator.

Extracts service versions from previous scan data and queries the NVD REST API
to surface known CVEs for each service.
"""

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m10_cve_correlator")

_NVD_URL = "https://services.nvd.nist.gov/rest/json/cves/2.0"


class Scanner:
    name = "CVE Correlator"
    phase = "custom"
    description = "Correlates detected service versions with known CVEs via NVD API"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _load_services(self) -> list[dict]:
        """Extract host/port/service/version tuples from scan_data.json."""
        services: list[dict] = []

        # Primary: scan_data.json (aggregated at end of scan)
        scan_data_file = self.output_dir / "scan_data.json"
        if scan_data_file.exists():
            try:
                with open(scan_data_file, encoding="utf-8") as f:
                    scan_data = json.load(f)
                for result in scan_data.get("results", []):
                    for finding in result.get("findings", []):
                        svc = finding.get("service") or finding.get("type", "")
                        ver = finding.get("version") or finding.get("banner", "")
                        port = finding.get("port", "")
                        if svc and ver and len(ver) > 2:
                            services.append({"service": svc, "version": ver, "port": port})
            except Exception as e:
                logger.warning("Could not read scan_data.json: %s", e)

        # Fallback: look for individual nmap JSON files
        if not services:
            for json_file in sorted(self.output_dir.glob("*.json")):
                if json_file.name == "scan_data.json":
                    continue
                try:
                    with open(json_file, encoding="utf-8") as f:
                        data = json.load(f)
                    for finding in data.get("findings", []):
                        svc = finding.get("service") or finding.get("type", "")
                        ver = finding.get("version") or finding.get("banner", "")
                        port = finding.get("port", "")
                        if svc and ver and len(ver) > 2:
                            services.append({"service": svc, "version": ver, "port": port})
                except Exception:
                    pass

        # Deduplicate
        seen = set()
        unique = []
        for s in services:
            key = f"{s['service']}:{s['version']}"
            if key not in seen:
                seen.add(key)
                unique.append(s)
        return unique

    def _query_nvd(self, service: str, version: str) -> list[dict]:
        """Query NVD CVE 2.0 API for a given service+version keyword."""
        keyword = f"{service} {version}".strip()
        try:
            r = requests.get(
                _NVD_URL,
                params={"keywordSearch": keyword, "resultsPerPage": 5},
                timeout=10,
                headers={"User-Agent": "CyberPulse/1.0"},
            )
            if r.status_code != 200:
                return []
            data = r.json()
            return data.get("vulnerabilities", [])
        except Exception as e:
            logger.debug("NVD query failed for %s: %s", keyword, e)
            return []

    @staticmethod
    def _cvss_score(cve_item: dict) -> float:
        metrics = cve_item.get("cve", {}).get("metrics", {})
        for key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if metrics.get(key):
                return float(metrics[key][0].get("cvssData", {}).get("baseScore", 0))
        return 0.0

    @staticmethod
    def _severity_from_score(score: float) -> str:
        if score >= 9.0:
            return "CRITICAL"
        if score >= 7.0:
            return "HIGH"
        if score >= 4.0:
            return "MEDIUM"
        if score > 0:
            return "LOW"
        return "INFO"

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        raw_lines: list[str] = []

        raw_lines.append("[+] CVE Correlator starting")
        services = self._load_services()
        raw_lines.append(f"[*] Found {len(services)} unique service versions to check")

        if not services:
            raw_lines.append("[!] No service version data found — skipping NVD lookup")
            return {"findings": [], "raw_output": "\n".join(raw_lines)}

        for svc in services[:10]:  # cap at 10 to respect NVD rate limit
            service = svc["service"]
            version = svc["version"]
            port = svc.get("port", "?")
            raw_lines.append(f"[*] Querying NVD: {service} {version} (port {port})")

            cves = self._query_nvd(service, version)
            for cve_item in cves:
                cve_id = cve_item.get("cve", {}).get("id", "UNKNOWN")
                score = self._cvss_score(cve_item)
                severity = self._severity_from_score(score)
                descriptions = cve_item.get("cve", {}).get("descriptions", [])
                description = next(
                    (d["value"] for d in descriptions if d.get("lang") == "en"),
                    "No English description available.",
                )
                findings.append({
                    "type": "cve_match",
                    "severity": severity,
                    "title": f"{cve_id} — {service} {version} (port {port})",
                    "cve": cve_id,
                    "cvss": score,
                    "service": service,
                    "version": version,
                    "port": port,
                    "description": description[:400],
                    "impact": f"Service {service} {version} has a known CVE with CVSS {score}.",
                    "recommendation": f"Update {service} to the latest stable version and apply vendor patches.",
                })
                raw_lines.append(f"    [{severity}] {cve_id} CVSS={score}")

            time.sleep(0.6)  # NVD allows ~100 req/min unauthenticated (0.6s safe)

        raw_lines.append(f"[+] Done — {len(findings)} CVE matches found")
        return {
            "findings": findings,
            "raw_output": "\n".join(raw_lines),
            "services_checked": len(services[:10]),
        }
