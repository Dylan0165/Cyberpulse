"""Foremost — file carving / recovery."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ForemostWrapper(BaseToolWrapper):
    name = "foremost"
    display_name = "Foremost"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["foremost"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        output_dir = kwargs.get("output_dir", "/tmp/foremost_out")
        return ["foremost", "-i", target, "-o", output_dir, "-v"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "files extracted" in output.lower() or "founded" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Bestanden hersteld via Foremost",
                detail=output[:2000],
                severity=Severity.INFO,
                recommendation="Controleer herstelde bestanden op gevoelige data.",
            ))
        return findings
