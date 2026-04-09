"""Arpspoof — ARP spoofing utility."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ArpspoofWrapper(BaseToolWrapper):
    name = "arpspoof"
    display_name = "Arpspoof"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["arpspoof"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=16, estimated_duration_s=10)

    def build_command(self, target: str, **kwargs) -> list[str]:
        gateway = kwargs.get("gateway", "")
        interface = kwargs.get("interface", "eth0")
        cmd = ["arpspoof", "-i", interface]
        if gateway:
            cmd.extend(["-t", target, gateway])
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        if stdout.strip() or stderr.strip():
            findings.append(ToolFinding(
                tool=self.name,
                title="ARP spoofing uitgevoerd",
                detail="ARP spoofing was succesvol — netwerk is kwetsbaar.",
                severity=Severity.HIGH,
                recommendation="Implementeer Dynamic ARP Inspection (DAI) op switches.",
            ))
        return findings
