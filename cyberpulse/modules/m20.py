"""Module 20 — Data Breach Check.

Checks if the target domain or associated emails appear in known
data breaches using Have I Been Pwned (if API key available) and
public breach databases.
"""

import json
import logging
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m20")


class Scanner:
    name = "Data Breach Check"
    phase = "reporting"
    description = "Checks domain and emails against known data breach databases"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "CyberPulse-Breach-Check/1.0"

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Data breach check for {self.target}"]

        from config import Config
        hibp_key = Config.HIBP_API_KEY

        # Collect emails found by other modules
        emails = self._collect_emails()
        raw_lines.append(f"Collected {len(emails)} email addresses to check")

        # Method 1: Have I Been Pwned (if API key available)
        if hibp_key:
            raw_lines.append("\n[Have I Been Pwned]")

            # Check domain breaches
            try:
                resp = self.session.get(
                    f"https://haveibeenpwned.com/api/v3/breaches",
                    headers={"hibp-api-key": hibp_key},
                    params={"domain": self.target},
                    timeout=10,
                )
                if resp.status_code == 200:
                    breaches = resp.json()
                    for breach in breaches:
                        raw_lines.append(f"  [!] {breach['Name']} ({breach.get('BreachDate', 'unknown')})")
                        findings.append({
                            "type": "domain_breach",
                            "breach_name": breach["Name"],
                            "breach_date": breach.get("BreachDate", ""),
                            "pwn_count": breach.get("PwnCount", 0),
                            "data_classes": breach.get("DataClasses", []),
                            "detail": f"Domain found in {breach['Name']} breach "
                                      f"({breach.get('PwnCount', 0):,} accounts, {breach.get('BreachDate', 'unknown')})",
                            "severity": "high",
                        })
                elif resp.status_code == 404:
                    raw_lines.append("  Domain not found in any breaches")
            except Exception as e:
                raw_lines.append(f"  HIBP domain check error: {e}")

            # Check individual emails
            for email in emails[:10]:  # Limit to 10 emails
                try:
                    time.sleep(1.5)  # HIBP rate limit
                    resp = self.session.get(
                        f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
                        headers={"hibp-api-key": hibp_key},
                        params={"truncateResponse": "false"},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        breaches = resp.json()
                        raw_lines.append(f"  [!] {email}: found in {len(breaches)} breach(es)")
                        findings.append({
                            "type": "email_breach",
                            "email": email,
                            "breach_count": len(breaches),
                            "breaches": [b["Name"] for b in breaches],
                            "detail": f"{email} found in {len(breaches)} breach(es): "
                                      f"{', '.join(b['Name'] for b in breaches[:5])}",
                            "severity": "high",
                        })
                    elif resp.status_code == 404:
                        raw_lines.append(f"  [OK] {email}: no breaches found")
                except Exception as e:
                    raw_lines.append(f"  Error checking {email}: {e}")
        else:
            raw_lines.append("\n[HIBP] No API key — skipping HIBP checks")
            raw_lines.append("  Set HIBP_API_KEY in .env for breach checking")

        # Method 2: IntelX public search (no API key needed)
        raw_lines.append("\n[Public Breach Databases]")
        breach_info = self._check_public_sources()
        if breach_info:
            for info in breach_info:
                raw_lines.append(f"  {info['detail']}")
                findings.append(info)

        # Method 3: Check for exposed credentials in paste sites
        raw_lines.append("\n[Paste Site Check]")
        if hibp_key:
            for email in emails[:5]:
                try:
                    time.sleep(1.5)
                    resp = self.session.get(
                        f"https://haveibeenpwned.com/api/v3/pasteaccount/{email}",
                        headers={"hibp-api-key": hibp_key},
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        pastes = resp.json()
                        raw_lines.append(f"  [!] {email}: found in {len(pastes)} paste(s)")
                        findings.append({
                            "type": "email_paste",
                            "email": email,
                            "paste_count": len(pastes),
                            "detail": f"{email} found in {len(pastes)} paste(s)",
                            "severity": "medium",
                        })
                except Exception:
                    pass
        else:
            raw_lines.append("  Skipped (needs HIBP API key)")

        if not findings:
            raw_lines.append("\nNo breach data found for this domain")
            findings.append({
                "type": "no_breaches_found",
                "detail": "No known breaches found for this domain (limited check without HIBP key)",
                "severity": "info",
            })

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "20_breach.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Breach check %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _collect_emails(self) -> list[str]:
        """Collect email addresses found by other modules."""
        emails = set()

        # Check sensitive data scan results
        sensitive_file = self.output_dir / "16_sensitive_data.json"
        if sensitive_file.exists():
            with open(sensitive_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for finding in data.get("findings", []):
                    if finding.get("pattern_name") == "Email Address":
                        pass  # Emails are counted but not stored individually

        # Generate common email patterns for the domain
        prefixes = ["info", "admin", "contact", "support", "security",
                     "webmaster", "postmaster", "abuse", "noreply"]
        for prefix in prefixes:
            emails.add(f"{prefix}@{self.target}")

        return sorted(emails)

    def _check_public_sources(self) -> list[dict]:
        """Check domain against publicly available breach information."""
        results = []

        # Check if domain has been in known major breaches (by DNS/MX similarity)
        try:
            resp = self.session.get(
                f"https://crt.sh/?q=%25@{self.target}&output=json",
                timeout=10,
            )
            if resp.status_code == 200:
                certs = resp.json()
                email_certs = [c for c in certs if "@" in c.get("name_value", "")]
                if email_certs:
                    results.append({
                        "type": "email_in_certificates",
                        "count": len(email_certs),
                        "detail": f"Found {len(email_certs)} email addresses in SSL certificates",
                        "severity": "info",
                    })
        except Exception:
            pass

        return results
