"""Wash — WPS-enabled AP scanner."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class WashWrapper(BaseToolWrapper):
    name = "wash"
    display_name = "Wash"
    category = ToolCategory.WIRELESS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["wash"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=16, estimated_duration_s=15)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "wlan0mon")
        return ["wash", "-i", interface]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        aps = []
        for line in stdout.splitlines():
            if line.strip() and not line.startswith("BSSID") and not line.startswith("-"):
                aps.append(line.strip())
        if aps:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Wash: {len(aps)} WPS-enabled APs",
                detail="\n".join(aps[:20]),
                severity=Severity.MEDIUM,
                recommendation="Schakel WPS uit op alle gedetecteerde access points.",
            ))
        return findings
