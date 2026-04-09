"""Medusa — parallel network login brute-forcer."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class MedusaWrapper(BaseToolWrapper):
    name = "medusa"
    display_name = "Medusa"
    category = ToolCategory.PASSWORD_CRACKING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["medusa"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        service = kwargs.get("service", "ssh")
        userlist = kwargs.get("userlist", "")
        passlist = kwargs.get("passlist", "")
        username = kwargs.get("username", "admin")

        cmd = ["medusa", "-h", target, "-M", service]
        if userlist:
            cmd.extend(["-U", str(userlist)])
        else:
            cmd.extend(["-u", username])
        if passlist:
            cmd.extend(["-P", str(passlist)])
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in (stdout + "\n" + stderr).splitlines():
            if "SUCCESS" in line.upper():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Login succesvol gevonden",
                    detail=line.strip(),
                    severity=Severity.CRITICAL,
                    description="Medusa heeft geldige credentials gevonden via brute-force.",
                    recommendation="Wijzig het wachtwoord en activeer account lockout / MFA.",
                    raw_output=line.strip()[:500],
                ))
        return findings
