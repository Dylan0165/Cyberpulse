"""John the Ripper — password cracking wrapper."""

import re
from pathlib import Path

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class JohnWrapper(BaseToolWrapper):
    name = "john"
    display_name = "John the Ripper"
    category = ToolCategory.PASSWORD_CRACKING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["john"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        """Target is the path to a hash file."""
        hashfile = kwargs.get("hashfile", target)
        wordlist = kwargs.get("wordlist", "")
        fmt = kwargs.get("format", "")

        cmd = ["john"]
        if fmt:
            cmd.extend(["--format=" + fmt])
        if wordlist:
            cmd.extend(["--wordlist=" + wordlist])
        cmd.append(str(hashfile))
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        # Parse cracked passwords: "password (username)"
        cracked = re.findall(r"^(.+?)\s+\((.+?)\)\s*$", combined, re.MULTILINE)
        for password, username in cracked:
            severity = Severity.CRITICAL if len(password) < 8 or password.lower() in ("password", "admin", "root", "123456") else Severity.HIGH
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Wachtwoord gekraakt voor {username}",
                detail=f"Gebruiker '{username}' heeft een zwak wachtwoord",
                severity=severity,
                description=f"John the Ripper heeft het wachtwoord van gebruiker '{username}' succesvol gekraakt. "
                            f"Dit duidt op een zwak wachtwoord dat niet voldoet aan beveiligingsstandaarden.",
                recommendation="Implementeer een sterk wachtwoordbeleid (min. 12 tekens, mix van letters/cijfers/symbolen). "
                               "Overweeg MFA te activeren.",
                raw_output=f"Gekraakt: {username}",
                references=["https://pages.nist.gov/800-63-3/sp800-63b.html"],
            ))

        if not cracked and "No password hashes loaded" in combined:
            findings.append(ToolFinding(
                tool=self.name,
                title="Geen hashes gevonden",
                detail="John kon geen wachtwoord-hashes laden uit het bestand",
                severity=Severity.INFO,
                description="Het opgegeven bestand bevat geen herkenbare wachtwoord-hashes.",
            ))

        return findings
