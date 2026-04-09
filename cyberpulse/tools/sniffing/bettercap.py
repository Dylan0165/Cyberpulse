"""Bettercap — network attack / monitoring framework."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class BettercapWrapper(BaseToolWrapper):
    name = "bettercap"
    display_name = "Bettercap"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["bettercap"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        caplet = kwargs.get("caplet", "")
        cmd = ["bettercap", "-eval", f"net.probe on; net.sniff on; sleep 10; quit", "-silent"]
        if caplet:
            cmd = ["bettercap", "-caplet", caplet, "-silent"]
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        if "endpoint detected" in stdout.lower() or "new host" in stdout.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Hosts ontdekt via Bettercap",
                detail=stdout[:2000],
                severity=Severity.INFO,
                recommendation="Controleer ontdekte hosts op ongeautoriseerde apparaten.",
            ))
        return findings
