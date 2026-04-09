"""Fierce — DNS reconnaissance (Python-native via fierce package)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class FierceWrapper(BaseToolWrapper):
    name = "fierce"
    display_name = "Fierce"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["fierce"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["fierce", "--domain", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        subdomains = set()
        for line in stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "." in line:
                parts = line.split()
                for p in parts:
                    if target in p:
                        subdomains.add(p.rstrip("."))
        if subdomains:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(subdomains)} subdomeinen gevonden",
                detail="\n".join(sorted(subdomains)[:50]),
                severity=Severity.INFO,
                recommendation="Controleer of alle subdomeinen bewust publiek toegankelijk zijn.",
            ))
        if "zone transfer" in stdout.lower() and "successful" in stdout.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="DNS Zone Transfer mogelijk",
                detail="Fierce kon een zone transfer uitvoeren.",
                severity=Severity.HIGH,
                recommendation="Beperk zone transfers tot geautoriseerde DNS-servers.",
            ))
        return findings
