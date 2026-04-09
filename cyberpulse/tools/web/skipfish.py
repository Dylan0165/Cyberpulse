"""Skipfish — web application scanner."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class SkipfishWrapper(BaseToolWrapper):
    name = "skipfish"
    display_name = "Skipfish"
    category = ToolCategory.WEB
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["skipfish"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        output_dir = kwargs.get("output_dir", "/tmp/skipfish_out")
        return ["skipfish", "-o", output_dir, "-Y", "-b", "i", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "issue" in output.lower() or "finding" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Skipfish web scan resultaten",
                detail=output[:3000],
                severity=Severity.MEDIUM,
                recommendation="Bekijk Skipfish HTML-rapport voor details.",
            ))
        return findings
