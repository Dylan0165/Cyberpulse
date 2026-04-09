"""Tcpdump — lightweight packet capture."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class TcpdumpWrapper(BaseToolWrapper):
    name = "tcpdump"
    display_name = "Tcpdump"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["tcpdump"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=15)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "")
        count = kwargs.get("count", "100")
        cmd = ["tcpdump", "-c", str(count), "-nn", "-q"]
        if interface:
            cmd.extend(["-i", interface])
        cmd.extend(["host", target])
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        protos = set()
        for line in stdout.splitlines():
            for proto in ["ftp", "telnet", "http "]:
                if proto in line.lower():
                    protos.add(proto.strip())
        for proto in protos:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Onversleuteld verkeer: {proto.upper()}",
                detail=f"Tcpdump zag {proto.upper()} packets",
                severity=Severity.MEDIUM,
                recommendation=f"Gebruik de versleutelde variant van {proto.upper()}.",
            ))
        return findings
