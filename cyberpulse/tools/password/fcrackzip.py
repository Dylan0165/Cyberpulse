"""fcrackzip — zip-bestand wachtwoord brute-forcer."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class FcrackzipWrapper(BaseToolWrapper):
    name = "fcrackzip"
    display_name = "Fcrackzip"
    category = ToolCategory.PASSWORD
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["fcrackzip"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        cmd = ["fcrackzip", "-u", "-D", "-p", wordlist, target]
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in stdout.splitlines():
            if "PASSWORD FOUND" in line.upper() or "pw ==" in line.lower():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Zip-wachtwoord gekraakt",
                    detail=f"fcrackzip vond het wachtwoord: {line.strip()}",
                    severity=Severity.CRITICAL,
                    recommendation="Gebruik een sterk wachtwoord voor zip-bestanden.",
                ))
        return findings
