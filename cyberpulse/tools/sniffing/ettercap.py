"""Ettercap — MITM attack suite."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class EttercapWrapper(BaseToolWrapper):
    name = "ettercap"
    display_name = "Ettercap"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["ettercap"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "eth0")
        return ["ettercap", "-T", "-q", "-i", interface, "-M", "arp:remote", f"/{target}//", "///"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        lower = output.lower()
        if "password" in lower or "credentials" in lower or "user" in lower:
            findings.append(ToolFinding(
                tool=self.name,
                title="Credentials onderschept via MITM",
                detail="Ettercap heeft credentials opgevangen.",
                severity=Severity.CRITICAL,
                recommendation="Gebruik TLS/HTTPS voor alle communicatie.",
            ))
        if "arp" in lower and "poison" in lower:
            findings.append(ToolFinding(
                tool=self.name,
                title="ARP poisoning succesvol",
                detail="Netwerk is kwetsbaar voor MITM-aanvallen.",
                severity=Severity.HIGH,
                recommendation="Implementeer 802.1X en Dynamic ARP Inspection.",
            ))
        return findings
