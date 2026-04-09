"""Reaver — WPS bruteforce."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ReaverWrapper(BaseToolWrapper):
    name = "reaver"
    display_name = "Reaver"
    category = ToolCategory.WIRELESS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["reaver"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "wlan0mon")
        return ["reaver", "-i", interface, "-b", target, "-vv"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "wps pin" in output.lower() or "wpa psk" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="WPS PIN / WPA sleutel gevonden",
                detail=output[:500],
                severity=Severity.CRITICAL,
                recommendation="Schakel WPS uit op het access point.",
            ))
        elif "locked" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="WPS vergrendeld na brute-force poging",
                detail="AP heeft WPS lock-out geactiveerd.",
                severity=Severity.MEDIUM,
                recommendation="WPS lockout werkt, maar schakel WPS volledig uit.",
            ))
        return findings
