"""Module 07 — WHOIS Lookup.

Retrieves domain registration information including registrar, dates,
nameservers, and contact details.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m07")


class Scanner:
    name = "WHOIS Lookup"
    phase = "reconnaissance"
    description = "Retrieves domain registration and ownership information"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"WHOIS lookup for {self.target}"]

        try:
            import whois
        except ImportError:
            raw_lines.append("python-whois not installed — skipping")
            return {"findings": [], "raw_output": "\n".join(raw_lines)}

        whois_data = {}
        try:
            w = whois.whois(self.target)

            # Extract fields safely
            whois_data = {
                "domain_name": self._first(w.domain_name),
                "registrar": w.registrar,
                "creation_date": str(self._first(w.creation_date) or ""),
                "expiration_date": str(self._first(w.expiration_date) or ""),
                "updated_date": str(self._first(w.updated_date) or ""),
                "name_servers": w.name_servers if isinstance(w.name_servers, list) else [w.name_servers] if w.name_servers else [],
                "status": w.status if isinstance(w.status, list) else [w.status] if w.status else [],
                "registrant": w.get("registrant_name", ""),
                "registrant_org": w.get("org", ""),
                "registrant_country": w.get("registrant_country", ""),
                "dnssec": w.get("dnssec", ""),
            }

            for key, val in whois_data.items():
                if val:
                    raw_lines.append(f"  {key}: {val}")

            findings.append({
                "type": "whois_info",
                "data": whois_data,
                "severity": "info",
            })

            # Check expiration
            from datetime import datetime
            exp = self._first(w.expiration_date)
            if exp and isinstance(exp, datetime):
                days = (exp - datetime.now()).days
                if days < 0:
                    findings.append({
                        "type": "domain_expired",
                        "detail": f"Domain expired {abs(days)} days ago",
                        "severity": "critical",
                    })
                elif days < 30:
                    findings.append({
                        "type": "domain_expiring_soon",
                        "detail": f"Domain expires in {days} days",
                        "severity": "medium",
                    })

            # DNSSEC check
            dnssec = str(w.get("dnssec", "")).lower()
            if "unsigned" in dnssec or not dnssec:
                findings.append({
                    "type": "dnssec_not_enabled",
                    "detail": "DNSSEC is not enabled",
                    "severity": "low",
                })

        except Exception as e:
            raw_lines.append(f"  WHOIS lookup failed: {e}")
            findings.append({
                "type": "whois_error",
                "detail": str(e),
                "severity": "info",
            })

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "07_whois.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "whois": whois_data}, f, indent=2, default=str)

        logger.info("WHOIS lookup %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _first(val):
        if isinstance(val, list):
            return val[0] if val else None
        return val
