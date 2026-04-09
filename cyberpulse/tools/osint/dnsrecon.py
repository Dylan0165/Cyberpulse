"""DNSrecon — DNS reconnaissance and enumeration."""

import json as json_mod
import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class DnsreconWrapper(BaseToolWrapper):
    name = "dnsrecon"
    display_name = "DNSrecon"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["dnsrecon"]
    default_timeout = 180
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=90)

    def build_command(self, target: str, **kwargs) -> list[str]:
        domain = target.replace("http://", "").replace("https://", "").split("/")[0]
        scan_type = kwargs.get("scan_type", "std,axfr,brt")

        return [
            "dnsrecon", "-d", domain,
            "-t", scan_type,
            "-j", "/dev/stdout",  # JSON output
        ]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        # Try JSON
        try:
            records = json_mod.loads(stdout)
            if isinstance(records, list):
                for rec in records:
                    rec_type = rec.get("type", "")

                    if rec_type == "AXFR" or "zone_transfer" in str(rec).lower():
                        findings.append(ToolFinding(
                            tool=self.name,
                            title="DNS Zone Transfer succesvol!",
                            detail="De DNS server staat zone transfers toe",
                            severity=Severity.HIGH,
                            description="De DNS server staat AXFR (zone transfer) toe. "
                                        "Een aanvaller kan hiermee alle DNS records opvragen.",
                            recommendation="Beperk zone transfers tot geautoriseerde secondary DNS servers.",
                            references=["https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/02-Configuration_and_Deployment_Management_Testing/10-Test_for_Subdomain_Takeover"],
                        ))
                return findings
        except json_mod.JSONDecodeError:
            pass

        # Parse text output
        combined = stdout + "\n" + stderr

        if "Zone Transfer was successful" in combined or "AXFR" in combined:
            findings.append(ToolFinding(
                tool=self.name,
                title="DNS Zone Transfer succesvol!",
                detail="De DNS server staat zone transfers toe",
                severity=Severity.HIGH,
                description="De DNS server staat AXFR toe. Alle DNS records zijn toegankelijk.",
                recommendation="Beperk zone transfers tot geautoriseerde servers.",
            ))

        # Count found records
        a_records = re.findall(r"A\s+(\S+)\s+(\d+\.\d+\.\d+\.\d+)", combined)
        mx_records = re.findall(r"MX\s+(\S+)", combined)
        txt_records = re.findall(r"TXT\s+(.+)", combined)

        if a_records:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(a_records)} DNS A-records gevonden",
                detail="DNS enumeratie resultaten",
                severity=Severity.INFO,
                description=f"DNSrecon vond {len(a_records)} A-records voor het domain.",
                raw_output="\n".join(f"{name} -> {ip}" for name, ip in a_records[:20]),
            ))

        # Check for missing SPF/DMARC
        has_spf = any("v=spf1" in t.lower() for t in txt_records)
        has_dmarc = any("v=dmarc1" in t.lower() for t in txt_records)

        if not has_spf:
            findings.append(ToolFinding(
                tool=self.name,
                title="Geen SPF record gevonden",
                detail="Het domain heeft geen SPF record",
                severity=Severity.MEDIUM,
                description="Er is geen SPF (Sender Policy Framework) record gevonden. "
                            "Dit maakt email spoofing mogelijk.",
                recommendation="Configureer een SPF record om email spoofing te voorkomen.",
            ))

        if not has_dmarc:
            findings.append(ToolFinding(
                tool=self.name,
                title="Geen DMARC record gevonden",
                detail="Het domain heeft geen DMARC record",
                severity=Severity.MEDIUM,
                description="Er is geen DMARC record gevonden. "
                            "DMARC beschermt tegen email spoofing en phishing.",
                recommendation="Configureer een DMARC record (bijv. v=DMARC1; p=reject).",
            ))

        return findings
