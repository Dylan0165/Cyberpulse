"""Maltego (CE) — OSINT visual link analysis (CLI transforms)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class MaltegoWrapper(BaseToolWrapper):
    name = "maltego"
    display_name = "Maltego"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["maltego"]
    default_timeout = 180
    resource_profile = ResourceProfile(estimated_ram_mb=512, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        # Maltego is primarily GUI; CLI usage is limited
        return ["maltego", "-i", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        if stdout.strip():
            findings.append(ToolFinding(
                tool=self.name,
                title="Maltego OSINT resultaten",
                detail=stdout[:3000],
                severity=Severity.INFO,
                recommendation="Gebruik Maltego GUI voor visuele analyse van relaties.",
            ))
        return findings
