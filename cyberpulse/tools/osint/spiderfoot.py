"""SpiderFoot — OSINT automation framework."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class SpiderfootWrapper(BaseToolWrapper):
    name = "spiderfoot"
    display_name = "SpiderFoot"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["spiderfoot"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        modules = kwargs.get("modules", "sfp_dns,sfp_whois,sfp_spider")
        return [
            "spiderfoot", "-s", target,
            "-m", modules,
            "-q", "-o", "json",
        ]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            if isinstance(data, list):
                for item in data[:100]:
                    dtype = item.get("type", "")
                    ddata = item.get("data", "")
                    if "leak" in dtype.lower() or "breach" in dtype.lower():
                        findings.append(ToolFinding(
                            tool=self.name,
                            title=f"Datalek gevonden: {dtype}",
                            detail=str(ddata)[:500],
                            severity=Severity.HIGH,
                            recommendation="Onderzoek de bron van het datalek.",
                        ))
        except (json.JSONDecodeError, TypeError):
            if stdout.strip():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="SpiderFoot resultaten",
                    detail=stdout[:3000],
                    severity=Severity.INFO,
                    recommendation="Analyseer SpiderFoot output handmatig.",
                ))
        return findings
