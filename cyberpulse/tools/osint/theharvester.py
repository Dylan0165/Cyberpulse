"""theHarvester — OSINT email and subdomain discovery."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class TheHarvesterWrapper(BaseToolWrapper):
    name = "theharvester"
    display_name = "theHarvester"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["theHarvester"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        domain = target.replace("http://", "").replace("https://", "").split("/")[0]
        sources = kwargs.get("sources", "all")
        limit = kwargs.get("limit", "200")

        return [
            "theHarvester",
            "-d", domain,
            "-b", sources,
            "-l", str(limit),
        ]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout

        # Extract emails
        emails = set()
        in_emails = False
        for line in combined.splitlines():
            if "Emails found" in line or "[*] Emails" in line:
                in_emails = True
                continue
            if in_emails and line.strip() and "@" in line:
                email = line.strip()
                if re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
                    emails.add(email)
            elif in_emails and not line.strip():
                in_emails = False

        if emails:
            severity = Severity.MEDIUM if len(emails) > 10 else Severity.LOW
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(emails)} e-mailadressen gevonden",
                detail=f"theHarvester vond {len(emails)} publiek beschikbare e-mailadressen",
                severity=severity,
                description=f"Er zijn {len(emails)} e-mailadressen gevonden die geassocieerd zijn met het target. "
                            "Deze informatie kan gebruikt worden voor phishing aanvallen.",
                recommendation="Beperk publiek beschikbare contactinformatie. "
                               "Train medewerkers in het herkennen van phishing.",
                raw_output="\n".join(sorted(emails)[:20]),
            ))

        # Extract subdomains/hosts
        hosts = set()
        in_hosts = False
        for line in combined.splitlines():
            if "Hosts found" in line or "[*] Hosts" in line:
                in_hosts = True
                continue
            if in_hosts and line.strip():
                host = line.strip().split(":")[0].strip()
                if "." in host and not host.startswith("["):
                    hosts.add(host)
            elif in_hosts and not line.strip():
                in_hosts = False

        if hosts:
            sensitive_hosts = [h for h in hosts if any(
                s in h.lower() for s in ("admin", "staging", "dev", "test", "backup", "internal", "vpn", "mail")
            )]
            severity = Severity.MEDIUM if sensitive_hosts else Severity.LOW

            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(hosts)} hosts/subdomains gevonden",
                detail=f"theHarvester vond {len(hosts)} hosts",
                severity=severity,
                description=f"Er zijn {len(hosts)} hosts/subdomains gevonden. " +
                            (f"Waarvan {len(sensitive_hosts)} mogelijk gevoelig." if sensitive_hosts else ""),
                recommendation="Controleer of alle subdomains beveiligd zijn. "
                               "Verwijder staging/test omgevingen van het publieke internet.",
                raw_output="\n".join(sorted(hosts)[:30]),
            ))

        return findings
