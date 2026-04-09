"""Trivy — container & filesystem vulnerability scanner."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_SEV = {"CRITICAL": Severity.CRITICAL, "HIGH": Severity.HIGH, "MEDIUM": Severity.MEDIUM, "LOW": Severity.LOW}


@register
class TrivyWrapper(BaseToolWrapper):
    name = "trivy"
    display_name = "Trivy"
    category = ToolCategory.VULN_ANALYSIS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["trivy"]
    default_timeout = 180
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        scan_type = kwargs.get("scan_type", "fs")
        return ["trivy", scan_type, "--format", "json", "--quiet", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            results = data.get("Results", [])
            for result in results:
                for vuln in result.get("Vulnerabilities", [])[:50]:
                    vid = vuln.get("VulnerabilityID", "?")
                    sev = _SEV.get(vuln.get("Severity", "").upper(), Severity.INFO)
                    pkg = vuln.get("PkgName", "?")
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"{vid} in {pkg}",
                        detail=vuln.get("Description", "")[:500],
                        severity=sev,
                        cve=vid if vid.startswith("CVE") else None,
                        recommendation=f"Update {pkg} naar {vuln.get('FixedVersion', 'nieuwste versie')}.",
                    ))
        except (json.JSONDecodeError, TypeError):
            pass
        return findings
