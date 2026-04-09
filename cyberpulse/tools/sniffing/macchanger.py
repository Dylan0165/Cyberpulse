"""Macchanger — MAC address spoofing."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class MacchangerWrapper(BaseToolWrapper):
    name = "macchanger"
    display_name = "Macchanger"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["macchanger"]
    default_timeout = 10
    resource_profile = ResourceProfile(estimated_ram_mb=8, estimated_duration_s=2)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", target)
        return ["macchanger", "-s", interface]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        if "current" in stdout.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="MAC-adres informatie",
                detail=stdout.strip()[:500],
                severity=Severity.INFO,
                recommendation="Overweeg MAC-filtering als extra beveiligingslaag.",
            ))
        return findings
