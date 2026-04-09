"""Aireplay-ng — WiFi deauth / injection."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class AireplayWrapper(BaseToolWrapper):
    name = "aireplay-ng"
    display_name = "Aireplay-ng"
    category = ToolCategory.WIRELESS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["aireplay-ng"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "wlan0mon")
        attack = kwargs.get("attack", "0")  # 0=deauth
        count = kwargs.get("count", "5")
        return ["aireplay-ng", f"-{attack}", str(count), "-a", target, interface]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        if "sending" in stdout.lower() or "ack" in stdout.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Deauthenticatie aanval uitgevoerd",
                detail=stdout[:500],
                severity=Severity.HIGH,
                recommendation="Gebruik 802.11w (PMF) om deauth-aanvallen te mitigeren.",
            ))
        return findings
