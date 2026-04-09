"""Lynis — Linux security auditing."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_SEV_MAP = {"warning": Severity.HIGH, "suggestion": Severity.MEDIUM}


@register
class LynisWrapper(BaseToolWrapper):
    name = "lynis"
    display_name = "Lynis"
    category = ToolCategory.VULN_ANALYSIS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["lynis"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["lynis", "audit", "system", "--no-colors", "--quick"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        hardening_idx = None
        for line in stdout.splitlines():
            clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            # Hardening index
            m = re.search(r'Hardening index\s*:\s*(\d+)', clean)
            if m:
                idx = int(m.group(1))
                sev = Severity.CRITICAL if idx < 50 else Severity.HIGH if idx < 70 else Severity.MEDIUM
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Lynis Hardening Index: {idx}/100",
                    detail=f"Score: {idx}/100",
                    severity=sev,
                    recommendation="Volg Lynis aanbevelingen om de score te verhogen.",
                ))
            # Warnings and suggestions
            if clean.lower().startswith("! "):
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Lynis Warning: {clean[2:80]}",
                    detail=clean,
                    severity=Severity.HIGH,
                    recommendation="Los deze Lynis waarschuwing op.",
                ))
            elif clean.lower().startswith("* ") and "[" in clean:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Lynis Suggestie: {clean[2:80]}",
                    detail=clean,
                    severity=Severity.MEDIUM,
                    recommendation="Overweeg deze aanbeveling te implementeren.",
                ))
        return findings
