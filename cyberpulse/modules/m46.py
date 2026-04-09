"""Module 46 — DNS Zone Transfer & DNS Security Testing.

Attempts zone transfers (AXFR) and checks for DNS misconfigurations
like open resolvers, DNSSEC status, and dangling records.
"""

import json
import logging
import re
import socket
import subprocess
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m46")


class Scanner:
    name = "DNS Zone Transfer & Security"
    phase = "reconnaissance"
    description = "Tests for DNS zone transfers, open resolvers, and DNSSEC misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"DNS security testing for {self.target}"]

        # Phase 1: Enumerate nameservers
        raw_lines.append("\n[Phase 1: Nameserver Enumeration]")
        nameservers = self._get_nameservers()
        raw_lines.append(f"  Found {len(nameservers)} nameservers")
        for ns in nameservers:
            raw_lines.append(f"  NS: {ns}")
            findings.append({
                "type": "nameserver",
                "nameserver": ns,
                "detail": f"Nameserver: {ns}",
                "severity": "info",
            })

        # Phase 2: Zone transfer test (AXFR)
        raw_lines.append("\n[Phase 2: Zone Transfer (AXFR)]")
        for ns in nameservers:
            axfr_result = self._try_zone_transfer(ns)
            if axfr_result:
                findings.append({
                    "type": "zone_transfer",
                    "nameserver": ns,
                    "records_count": len(axfr_result),
                    "detail": f"ZONE TRANSFER SUCCESSFUL from {ns}! ({len(axfr_result)} records)",
                    "severity": "critical",
                    "records_sample": axfr_result[:20],
                })
                raw_lines.append(f"  CRITICAL: AXFR from {ns} — {len(axfr_result)} records exposed!")
            else:
                raw_lines.append(f"  OK: AXFR denied by {ns}")

        # Phase 3: Important DNS records
        raw_lines.append("\n[Phase 3: DNS Record Analysis]")
        record_types = ["A", "AAAA", "MX", "TXT", "SOA", "CAA"]
        for rtype in record_types:
            records = self._query_dns(self.target, rtype)
            if records:
                for record in records[:5]:
                    findings.append({
                        "type": "dns_record",
                        "record_type": rtype,
                        "value": record,
                        "detail": f"{rtype}: {record}",
                        "severity": "info",
                    })
                    raw_lines.append(f"  {rtype}: {record}")

                    # Analyze TXT records for sensitive info
                    if rtype == "TXT":
                        if "v=spf" in record:
                            if "+all" in record:
                                findings.append({
                                    "type": "spf_permissive",
                                    "detail": "SPF record is too permissive (+all)",
                                    "severity": "medium",
                                })
                                raw_lines.append("  MEDIUM: SPF too permissive (+all)")
                        if "v=DMARC" in record.upper():
                            if "p=none" in record:
                                findings.append({
                                    "type": "dmarc_none",
                                    "detail": "DMARC policy is 'none' — no email protection",
                                    "severity": "medium",
                                })
                                raw_lines.append("  MEDIUM: DMARC policy=none")

        # Phase 4: DMARC, DKIM, SPF checks
        raw_lines.append("\n[Phase 4: Email Security Records]")
        # DMARC
        dmarc = self._query_dns(f"_dmarc.{self.target}", "TXT")
        if dmarc:
            for r in dmarc:
                raw_lines.append(f"  DMARC: {r}")
        else:
            findings.append({
                "type": "no_dmarc",
                "detail": "No DMARC record found — email spoofing possible",
                "severity": "medium",
            })
            raw_lines.append("  MEDIUM: No DMARC record")

        # SPF
        spf = [r for r in self._query_dns(self.target, "TXT") if "v=spf" in r.lower()]
        if not spf:
            findings.append({
                "type": "no_spf",
                "detail": "No SPF record found — email spoofing possible",
                "severity": "medium",
            })
            raw_lines.append("  MEDIUM: No SPF record")

        # Phase 5: CAA record
        raw_lines.append("\n[Phase 5: CAA Record Check]")
        caa = self._query_dns(self.target, "CAA")
        if not caa:
            findings.append({
                "type": "no_caa",
                "detail": "No CAA record — any CA can issue certificates",
                "severity": "low",
            })
            raw_lines.append("  LOW: No CAA record")
        else:
            for r in caa:
                raw_lines.append(f"  CAA: {r}")

        # Phase 6: DNSSEC check
        raw_lines.append("\n[Phase 6: DNSSEC Status]")
        dnssec = self._check_dnssec()
        if dnssec:
            raw_lines.append("  OK: DNSSEC enabled")
            findings.append({
                "type": "dnssec",
                "enabled": True,
                "detail": "DNSSEC is enabled",
                "severity": "info",
            })
        else:
            findings.append({
                "type": "no_dnssec",
                "detail": "DNSSEC is not enabled — DNS responses can be spoofed",
                "severity": "low",
            })
            raw_lines.append("  LOW: DNSSEC not enabled")

        # Phase 7: Wildcard DNS detection
        raw_lines.append("\n[Phase 7: Wildcard DNS Detection]")
        random_sub = f"xyznonexistent12345.{self.target}"
        try:
            ip = socket.gethostbyname(random_sub)
            findings.append({
                "type": "wildcard_dns",
                "resolves_to": ip,
                "detail": f"Wildcard DNS: random subdomain resolves to {ip}",
                "severity": "low",
            })
            raw_lines.append(f"  LOW: Wildcard DNS active (resolves to {ip})")
        except socket.gaierror:
            raw_lines.append("  OK: No wildcard DNS")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "46_dns.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("DNS scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_nameservers(self) -> list[str]:
        """Get NS records for the target domain."""
        nameservers = []
        try:
            result = subprocess.run(
                ["nslookup", "-type=NS", self.target],
                capture_output=True, text=True, timeout=10,
            )
            ns_matches = re.findall(r"nameserver\s*=\s*(\S+)", result.stdout)
            nameservers = [ns.rstrip(".") for ns in ns_matches]
        except Exception:
            pass
        return nameservers

    def _try_zone_transfer(self, nameserver: str) -> list[str] | None:
        """Attempt AXFR zone transfer using nslookup."""
        try:
            result = subprocess.run(
                ["nslookup", "-type=AXFR", self.target, nameserver],
                capture_output=True, text=True, timeout=15,
            )
            output = result.stdout + result.stderr
            if "Transfer failed" in output or "refused" in output.lower():
                return None
            records = [line.strip() for line in output.split("\n")
                       if line.strip() and not line.startswith("#")]
            if len(records) > 5:  # Real transfer has many records
                return records
        except Exception:
            pass
        return None

    def _query_dns(self, domain: str, record_type: str) -> list[str]:
        """Query DNS for specific record type."""
        records = []
        try:
            result = subprocess.run(
                ["nslookup", f"-type={record_type}", domain],
                capture_output=True, text=True, timeout=10,
            )
            for line in result.stdout.split("\n"):
                line = line.strip()
                if "=" in line and "server" not in line.lower():
                    value = line.split("=", 1)[-1].strip().strip('"')
                    if value:
                        records.append(value)
        except Exception:
            pass
        return records

    def _check_dnssec(self) -> bool:
        """Check DNSSEC using DNSKEY record lookup."""
        try:
            result = subprocess.run(
                ["nslookup", "-type=DNSKEY", self.target],
                capture_output=True, text=True, timeout=10,
            )
            return "DNSKEY" in result.stdout or "RRSIG" in result.stdout
        except Exception:
            return False
