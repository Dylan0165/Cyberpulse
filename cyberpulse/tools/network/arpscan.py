"""Arp-scan — network host discovery via ARP."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ArpscanWrapper(BaseToolWrapper):
    name = "arpscan"
    display_name = "Arp-scan"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["arp-scan"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=16, estimated_duration_s=10)

    def build_command(self, target: str, **kwargs) -> list[str]:
        if target in ("localnet", "local", ""):
            return ["arp-scan", "--localnet"]
        return ["arp-scan", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        hosts = []
        for line in stdout.splitlines():
            match = re.match(r"(\d+\.\d+\.\d+\.\d+)\s+([0-9a-f:]{17})\s*(.*)", line, re.IGNORECASE)
            if match:
                hosts.append({"ip": match.group(1), "mac": match.group(2), "vendor": match.group(3).strip()})
        if hosts:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(hosts)} hosts op het netwerk",
                detail="ARP scan resultaten",
                severity=Severity.INFO,
                raw_output="\n".join(f"{h['ip']} {h['mac']} {h['vendor']}" for h in hosts[:30]),
            ))
        return findings
