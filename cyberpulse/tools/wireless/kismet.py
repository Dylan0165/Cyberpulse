"""Kismet — wireless network sniffer / IDS."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class KismetWrapper(BaseToolWrapper):
    name = "kismet"
    display_name = "Kismet"
    category = ToolCategory.WIRELESS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["kismet"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        source = kwargs.get("source", "wlan0")
        return ["kismet", "-c", source, "--override", "log_types=kismet", "-t", "30"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "open" in output.lower() and "network" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Open WiFi netwerken gedetecteerd",
                detail=output[:1000],
                severity=Severity.HIGH,
                recommendation="Gebruik WPA3/WPA2 encryptie op alle netwerken.",
            ))
        if output.strip():
            findings.append(ToolFinding(
                tool=self.name,
                title="Kismet wireless scan resultaten",
                detail=output[:2000],
                severity=Severity.INFO,
                recommendation="Analyseer Kismet log bestanden voor details.",
            ))
        return findings
