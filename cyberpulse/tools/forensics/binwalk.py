"""Binwalk — firmware analysis / embedded file extraction."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class BinwalkWrapper(BaseToolWrapper):
    name = "binwalk"
    display_name = "Binwalk"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["binwalk"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        extract = kwargs.get("extract", False)
        cmd = ["binwalk"]
        if extract:
            cmd.append("-e")
        cmd.append(target)
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        embedded = []
        for line in stdout.splitlines():
            line = line.strip()
            if line and not line.startswith("DECIMAL") and not line.startswith("-"):
                parts = line.split(None, 2)
                if len(parts) >= 3 and parts[0].isdigit():
                    embedded.append(parts[2])
        if embedded:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Binwalk: {len(embedded)} embedded bestanden",
                detail="\n".join(embedded[:30]),
                severity=Severity.MEDIUM if any("key" in e.lower() or "certificate" in e.lower() for e in embedded) else Severity.INFO,
                recommendation="Controleer embedded bestanden op gevoelige data.",
            ))
        return findings
