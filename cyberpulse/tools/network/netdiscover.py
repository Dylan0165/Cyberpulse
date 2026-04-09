"""Netdiscover — ARP-based network host discovery."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class NetdiscoverWrapper(BaseToolWrapper):
    name = "netdiscover"
    display_name = "Netdiscover"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["netdiscover"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["netdiscover", "-r", target, "-P"]  # -P = parseable output

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        hosts = []
        for line in stdout.splitlines():
            parts = line.strip().split()
            if len(parts) >= 2 and re.match(r"\d+\.\d+\.\d+\.\d+", parts[0]):
                hosts.append({"ip": parts[0], "mac": parts[1] if len(parts) > 1 else ""})
        if hosts:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(hosts)} hosts gevonden op het netwerk",
                detail="Netdiscover ARP scan resultaten",
                severity=Severity.INFO,
                description=f"Er zijn {len(hosts)} actieve hosts gevonden op het lokale netwerk.",
                raw_output="\n".join(f"{h['ip']} ({h['mac']})" for h in hosts[:30]),
            ))
        return findings
