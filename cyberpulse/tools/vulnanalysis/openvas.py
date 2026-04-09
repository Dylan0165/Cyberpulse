"""OpenVAS (GVM) — vulnerability scanner via gvm-cli."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_SEV_MAP = {
    "Log": Severity.INFO, "Low": Severity.LOW, "Medium": Severity.MEDIUM,
    "High": Severity.HIGH, "Critical": Severity.CRITICAL,
}


@register
class OpenvasWrapper(BaseToolWrapper):
    name = "openvas"
    display_name = "OpenVAS"
    category = ToolCategory.VULN_ANALYSIS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["gvm-cli"]
    default_timeout = 600
    resource_profile = ResourceProfile(estimated_ram_mb=512, estimated_duration_s=300)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["gvm-cli", "--gmp-username", "admin", "--gmp-password", "admin",
                "socket", "--xml", f'<get_results filter="host={target}"/>']

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        # Simple XML-like parsing for results
        import re
        results = re.findall(r'<result.*?</result>', stdout, re.DOTALL)
        for r in results[:50]:
            name_m = re.search(r'<name>(.*?)</name>', r)
            sev_m = re.search(r'<threat>(.*?)</threat>', r)
            desc_m = re.search(r'<description>(.*?)</description>', r)
            name = name_m.group(1) if name_m else "Onbekend"
            sev_str = sev_m.group(1) if sev_m else "Medium"
            desc = desc_m.group(1) if desc_m else ""
            findings.append(ToolFinding(
                tool=self.name,
                title=f"OpenVAS: {name[:100]}",
                detail=desc[:500],
                severity=_SEV_MAP.get(sev_str, Severity.MEDIUM),
                recommendation="Remedieer deze kwetsbaarheid volgens de OpenVAS aanbeveling.",
            ))
        return findings
