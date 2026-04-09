"""Ophcrack — rainbow table password cracker."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class OphcrackWrapper(BaseToolWrapper):
    name = "ophcrack"
    display_name = "Ophcrack"
    category = ToolCategory.PASSWORD
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["ophcrack"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=512, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        tables = kwargs.get("tables", "/usr/share/ophcrack/tables")
        return ["ophcrack", "-g", "-d", tables, "-f", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in stdout.splitlines():
            if ":" in line and "not found" not in line.lower():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Windows-wachtwoord gekraakt",
                    detail=line.strip()[:200],
                    severity=Severity.CRITICAL,
                    recommendation="Gebruik sterkere wachtwoorden die niet in rainbow tables staan.",
                ))
        return findings
