"""Module 03 — DNS Enumeration.

Performs DNS lookups: A, AAAA, MX, NS, TXT, SOA, CNAME, and attempts zone transfer.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m03")


class Scanner:
    name = "DNS Enumeration"
    phase = "reconnaissance"
    description = "Enumerates DNS records and checks for misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"DNS enumeration for {self.target}"]

        try:
            import dns.resolver
            import dns.zone
            import dns.query
        except ImportError:
            raw_lines.append("dnspython not installed — skipping DNS enumeration")
            return {"findings": [], "raw_output": "\n".join(raw_lines)}

        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 10

        record_types = ["A", "AAAA", "MX", "NS", "TXT", "SOA", "CNAME"]
        all_records = {}

        for rtype in record_types:
            try:
                answers = resolver.resolve(self.target, rtype)
                records = [str(r) for r in answers]
                all_records[rtype] = records
                raw_lines.append(f"  {rtype}: {', '.join(records)}")

                for record in records:
                    findings.append({
                        "type": "dns_record",
                        "record_type": rtype,
                        "value": record,
                        "severity": "info",
                    })

                    # Security checks on TXT records
                    if rtype == "TXT":
                        txt_val = record.strip('"')
                        if "v=spf1" in txt_val:
                            if "+all" in txt_val:
                                findings.append({
                                    "type": "dns_misconfiguration",
                                    "detail": "SPF record uses +all (allows any sender)",
                                    "value": txt_val,
                                    "severity": "high",
                                })
                            elif "~all" in txt_val:
                                findings.append({
                                    "type": "dns_misconfiguration",
                                    "detail": "SPF record uses ~all (softfail, not strict)",
                                    "value": txt_val,
                                    "severity": "medium",
                                })
                        if "_dmarc" not in self.target and rtype == "TXT":
                            pass  # Check DMARC separately

            except dns.resolver.NoAnswer:
                raw_lines.append(f"  {rtype}: no answer")
            except dns.resolver.NXDOMAIN:
                raw_lines.append(f"  {rtype}: NXDOMAIN")
                break
            except Exception as e:
                raw_lines.append(f"  {rtype}: error ({e})")

        # Check DMARC
        try:
            dmarc_answers = resolver.resolve(f"_dmarc.{self.target}", "TXT")
            for r in dmarc_answers:
                val = str(r).strip('"')
                raw_lines.append(f"  DMARC: {val}")
                findings.append({
                    "type": "dns_record",
                    "record_type": "DMARC",
                    "value": val,
                    "severity": "info",
                })
                if "p=none" in val:
                    findings.append({
                        "type": "dns_misconfiguration",
                        "detail": "DMARC policy is 'none' (no enforcement)",
                        "severity": "medium",
                    })
        except Exception:
            findings.append({
                "type": "dns_misconfiguration",
                "detail": "No DMARC record found",
                "severity": "medium",
            })
            raw_lines.append("  DMARC: not found")

        # Attempt zone transfer
        ns_records = all_records.get("NS", [])
        for ns in ns_records:
            ns = ns.rstrip(".")
            try:
                zone = dns.zone.from_xfr(dns.query.xfr(ns, self.target, timeout=5))
                zone_records = [str(name) for name in zone.nodes.keys()]
                findings.append({
                    "type": "zone_transfer",
                    "nameserver": ns,
                    "records_count": len(zone_records),
                    "severity": "critical",
                    "detail": f"Zone transfer allowed on {ns}! {len(zone_records)} records exposed",
                })
                raw_lines.append(f"  AXFR {ns}: ALLOWED ({len(zone_records)} records)")
            except Exception:
                raw_lines.append(f"  AXFR {ns}: denied (good)")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "03_dns.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "records": all_records}, f, indent=2)

        logger.info("DNS enumeration %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}
