"""Ghidra headless — NSA reverse engineering (headless analyzer)."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class GhidraWrapper(BaseToolWrapper):
    name = "ghidra"
    display_name = "Ghidra"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["analyzeHeadless"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=1024, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        project_dir = kwargs.get("project_dir", "/tmp/ghidra_project")
        project_name = kwargs.get("project_name", "cyberpulse")
        return [
            "analyzeHeadless", project_dir, project_name,
            "-import", target,
            "-postScript", "ExportFunctionList.py",
        ]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        dangerous = ["system", "exec", "popen", "gets", "strcpy", "sprintf"]
        found = [f for f in dangerous if f in output.lower()]
        if found:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Ghidra: onveilige functies ({', '.join(found)})",
                detail=f"Gevonden in binary: {', '.join(found)}",
                severity=Severity.HIGH,
                recommendation="Controleer gebruik van onveilige functies.",
            ))
        return findings
