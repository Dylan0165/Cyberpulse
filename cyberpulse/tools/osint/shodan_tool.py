"""Shodan CLI — Internet-wide device search via API."""

import json, os
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ShodanWrapper(BaseToolWrapper):
    name = "shodan"
    display_name = "Shodan"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.API
    required_binaries = ["shodan"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=15)

    def is_available(self) -> bool:
        return bool(os.environ.get("SHODAN_API_KEY")) and super().is_available()

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["shodan", "host", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        open_ports = []
        vulns = []
        for line in stdout.splitlines():
            line_l = line.lower().strip()
            if line_l.startswith("ports:"):
                open_ports = [p.strip() for p in line.split(":", 1)[1].split(",")]
            if "vulns:" in line_l or "cve-" in line_l:
                vulns.append(line.strip())
        if open_ports:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Shodan: {len(open_ports)} open poorten",
                detail=f"Poorten: {', '.join(open_ports)}",
                severity=Severity.MEDIUM,
                recommendation="Beperk publiek bereikbare poorten tot minimaal vereiste.",
            ))
        if vulns:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Shodan: {len(vulns)} bekende kwetsbaarheden",
                detail="\n".join(vulns[:20]),
                severity=Severity.HIGH,
                recommendation="Patch de gevonden CVE's zo snel mogelijk.",
            ))
        return findings
