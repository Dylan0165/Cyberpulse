"""Unicornscan — async port scanner."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class UnicornscanWrapper(BaseToolWrapper):
    name = "unicornscan"
    display_name = "Unicornscan"
    category = ToolCategory.NETWORK
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["unicornscan"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        ports = kwargs.get("ports", "1-65535")
        rate = kwargs.get("rate", "500")
        return ["unicornscan", "-mT", f"-p{ports}", f"-r{rate}", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        ports = []
        for line in stdout.splitlines():
            if "open" in line.lower():
                parts = line.split()
                for p in parts:
                    if "/" in p and p.split("/")[0].isdigit():
                        ports.append(p)
        if ports:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Unicornscan: {len(ports)} open poorten",
                detail="\n".join(ports[:50]),
                severity=Severity.MEDIUM,
                recommendation="Controleer of alle open poorten noodzakelijk zijn.",
            ))
        return findings
