"""Zmap — fast single-port network scanner."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ZmapWrapper(BaseToolWrapper):
    name = "zmap"
    display_name = "Zmap"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["zmap"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        port = kwargs.get("port", "80")
        bandwidth = "1M" if self._laptop_mode else kwargs.get("bandwidth", "10M")
        return ["zmap", "-B", bandwidth, "-p", str(port), target, "-q"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        port = kwargs.get("port", "80")
        hosts = [l.strip() for l in stdout.splitlines() if l.strip() and re.match(r"\d+\.\d+\.\d+\.\d+", l.strip())]
        if hosts:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(hosts)} hosts met open poort {port}",
                detail=f"Zmap vond {len(hosts)} hosts",
                severity=Severity.INFO,
                raw_output="\n".join(hosts[:50]),
            ))
        return findings
