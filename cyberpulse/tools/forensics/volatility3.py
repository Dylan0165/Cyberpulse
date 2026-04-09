"""Volatility3 — memory forensics framework."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class Volatility3Wrapper(BaseToolWrapper):
    name = "volatility3"
    display_name = "Volatility 3"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["vol"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=512, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        plugin = kwargs.get("plugin", "windows.pslist.PsList")
        return ["vol", "-f", target, plugin, "-r", "json"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            if isinstance(data, list) and data:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Volatility: {len(data)} items gevonden",
                    detail=json.dumps(data[:10], indent=2)[:2000],
                    severity=Severity.INFO,
                    recommendation="Analyseer de memory dump voor verdachte processen.",
                ))
        except (json.JSONDecodeError, TypeError):
            if stdout.strip():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Volatility analyse resultaat",
                    detail=stdout[:3000],
                    severity=Severity.INFO,
                    recommendation="Bekijk Volatility output handmatig.",
                ))
        return findings
