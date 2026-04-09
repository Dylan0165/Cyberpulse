"""CVE Scraper — fetches recent CVE data from NVD and CISA feeds."""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
import feedparser

from config import Config

logger = logging.getLogger("cyberpulse.scraper.cve")


class CVEScraper:
    """Scrapes CVE data from public feeds and stores locally as JSON."""

    def __init__(self):
        self.output_dir = Config.DATA_DIR / "scraped"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.output_file = self.output_dir / "cve_feed.json"
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CyberPulse-CVE-Scraper/1.0"

    def run(self) -> int:
        """Fetch and store recent CVEs. Returns count of items processed."""
        all_cves = self._load_existing()
        existing_ids = {c["cve_id"] for c in all_cves}
        new_count = 0

        # Source 1: CISA Known Exploited Vulnerabilities
        cisa_cves = self._fetch_cisa_kev()
        for cve in cisa_cves:
            if cve["cve_id"] not in existing_ids:
                all_cves.append(cve)
                existing_ids.add(cve["cve_id"])
                new_count += 1

        # Source 2: NVD recent CVEs via RSS-like feed
        nvd_cves = self._fetch_nvd_recent()
        for cve in nvd_cves:
            if cve["cve_id"] not in existing_ids:
                all_cves.append(cve)
                existing_ids.add(cve["cve_id"])
                new_count += 1

        # Source 3: CERT RSS feed
        cert_cves = self._fetch_cert_feed()
        for cve in cert_cves:
            if cve["cve_id"] not in existing_ids:
                all_cves.append(cve)
                existing_ids.add(cve["cve_id"])
                new_count += 1

        # Keep only last 2000 entries, sorted by date
        all_cves.sort(key=lambda c: c.get("published", ""), reverse=True)
        all_cves = all_cves[:2000]

        with open(self.output_file, "w", encoding="utf-8") as f:
            json.dump(all_cves, f, indent=2, ensure_ascii=False)

        logger.info("CVE scraper: %d new CVEs, %d total stored", new_count, len(all_cves))
        return new_count

    def _load_existing(self) -> list:
        if self.output_file.exists():
            with open(self.output_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    def _fetch_cisa_kev(self) -> list[dict]:
        """Fetch CISA Known Exploited Vulnerabilities catalog."""
        cves = []
        try:
            resp = self.session.get(
                "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                for vuln in data.get("vulnerabilities", []):
                    cves.append({
                        "cve_id": vuln.get("cveID", ""),
                        "summary": vuln.get("shortDescription", ""),
                        "severity": "critical",  # All CISA KEV entries are actively exploited
                        "affected_products": [vuln.get("product", "")],
                        "vendor": vuln.get("vendorProject", ""),
                        "published": vuln.get("dateAdded", ""),
                        "source": "CISA-KEV",
                        "actively_exploited": True,
                    })
                logger.info("CISA KEV: fetched %d entries", len(cves))
        except Exception as e:
            logger.warning("CISA KEV fetch failed: %s", e)
        return cves

    def _fetch_nvd_recent(self) -> list[dict]:
        """Fetch recent CVEs from NVD."""
        cves = []
        try:
            # NVD API 2.0
            end = datetime.now(timezone.utc)
            start = end - timedelta(days=7)
            params = {
                "pubStartDate": start.strftime("%Y-%m-%dT00:00:00.000"),
                "pubEndDate": end.strftime("%Y-%m-%dT23:59:59.999"),
                "resultsPerPage": 100,
            }
            resp = self.session.get(
                "https://services.nvd.nist.gov/rest/json/cves/2.0",
                params=params,
                timeout=30,
            )
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("vulnerabilities", []):
                    cve_item = item.get("cve", {})
                    cve_id = cve_item.get("id", "")
                    descriptions = cve_item.get("descriptions", [])
                    summary = ""
                    for desc in descriptions:
                        if desc.get("lang") == "en":
                            summary = desc.get("value", "")
                            break

                    # Extract severity from CVSS
                    severity = "medium"
                    metrics = cve_item.get("metrics", {})
                    for metric_key in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
                        metric_list = metrics.get(metric_key, [])
                        if metric_list:
                            base_score = metric_list[0].get("cvssData", {}).get("baseScore", 0)
                            if base_score >= 9.0:
                                severity = "critical"
                            elif base_score >= 7.0:
                                severity = "high"
                            elif base_score >= 4.0:
                                severity = "medium"
                            else:
                                severity = "low"
                            break

                    # Extract affected products
                    affected = []
                    configurations = cve_item.get("configurations", [])
                    for config in configurations:
                        for node in config.get("nodes", []):
                            for match in node.get("cpeMatch", []):
                                criteria = match.get("criteria", "")
                                parts = criteria.split(":")
                                if len(parts) >= 5:
                                    affected.append(parts[4])

                    cves.append({
                        "cve_id": cve_id,
                        "summary": summary[:500],
                        "severity": severity,
                        "affected_products": affected[:10],
                        "published": cve_item.get("published", ""),
                        "source": "NVD",
                    })
                logger.info("NVD: fetched %d recent CVEs", len(cves))
        except Exception as e:
            logger.warning("NVD fetch failed: %s", e)
        return cves

    def _fetch_cert_feed(self) -> list[dict]:
        """Fetch CVEs from US-CERT RSS feed."""
        cves = []
        try:
            feed = feedparser.parse("https://www.cisa.gov/cybersecurity-advisories/all.xml")
            for entry in feed.entries[:50]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")
                published = entry.get("published", "")

                # Extract CVE IDs from title/summary
                import re
                cve_ids = re.findall(r"CVE-\d{4}-\d+", f"{title} {summary}")
                for cve_id in cve_ids:
                    cves.append({
                        "cve_id": cve_id,
                        "summary": f"{title}: {summary[:300]}",
                        "severity": "high",
                        "affected_products": [],
                        "published": published,
                        "source": "US-CERT",
                    })
            logger.info("CERT RSS: found %d CVE references", len(cves))
        except Exception as e:
            logger.warning("CERT RSS fetch failed: %s", e)
        return cves
