"""Hping3 — TCP/IP packet assembler/analyzer."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class Hping3Wrapper(BaseToolWrapper):
    name = "hping3"
    display_name = "Hping3"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["hping3"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        port = kwargs.get("port", "80")
        count = kwargs.get("count", "5")
        return ["hping3", "--syn", "-p", str(port), "-c", str(count), target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr
        if "flags=SA" in combined:
            port = kwargs.get("port", "80")
            findings.append(ToolFinding(
                tool=self.name, title=f"Poort {port} is open (SYN-ACK)",
                detail=f"Hping3 SYN scan bevestigt open poort {port}",
                severity=Severity.INFO, port=int(port),
            ))
        if "flags=RA" in combined:
            port = kwargs.get("port", "80")
            findings.append(ToolFinding(
                tool=self.name, title=f"Poort {port} is gesloten (RST-ACK)",
                detail=f"Poort {port} is dicht", severity=Severity.INFO,
            ))
        return findings
