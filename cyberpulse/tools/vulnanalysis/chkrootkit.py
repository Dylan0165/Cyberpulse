"""Chkrootkit — rootkit checker."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ChkrootkitWrapper(BaseToolWrapper):
    name = "chkrootkit"
    display_name = "Chkrootkit"
    category = ToolCategory.VULN_ANALYSIS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["chkrootkit"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["chkrootkit", "-q"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in stdout.splitlines():
            line = line.strip()
            if "infected" in line.lower():
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Rootkit gedetecteerd: {line[:80]}",
                    detail=line,
                    severity=Severity.CRITICAL,
                    recommendation="Isoleer systeem en voer forensisch onderzoek uit.",
                ))
            elif "suspicious" in line.lower():
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Verdacht: {line[:80]}",
                    detail=line,
                    severity=Severity.HIGH,
                    recommendation="Onderzoek verdachte bestanden/processen.",
                ))
        return findings
