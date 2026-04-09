"""Grype — container image vulnerability scanner."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_SEV = {"Critical": Severity.CRITICAL, "High": Severity.HIGH, "Medium": Severity.MEDIUM, "Low": Severity.LOW}


@register
class GrypeWrapper(BaseToolWrapper):
    name = "grype"
    display_name = "Grype"
    category = ToolCategory.VULN_ANALYSIS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["grype"]
    default_timeout = 180
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["grype", target, "-o", "json", "--quiet"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            for match in data.get("matches", [])[:50]:
                vuln = match.get("vulnerability", {})
                vid = vuln.get("id", "?")
                sev = _SEV.get(vuln.get("severity", ""), Severity.INFO)
                pkg = match.get("artifact", {}).get("name", "?")
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"{vid} in {pkg}",
                    detail=vuln.get("description", "")[:500],
                    severity=sev,
                    cve=vid if vid.startswith("CVE") else None,
                    recommendation=f"Update {pkg} naar een gepatche versie.",
                ))
        except (json.JSONDecodeError, TypeError):
            pass
        return findings
