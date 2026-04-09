"""Steghide — steganography tool."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class SteghideWrapper(BaseToolWrapper):
    name = "steghide"
    display_name = "Steghide"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["steghide"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=10)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["steghide", "info", target, "-f"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "embedded" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Verborgen data gedetecteerd",
                detail=output[:1000],
                severity=Severity.MEDIUM,
                recommendation="Extraheer en analyseer verborgen data.",
            ))
        return findings
