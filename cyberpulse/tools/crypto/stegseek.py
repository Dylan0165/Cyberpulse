"""Stegseek — fast steghide cracker."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class StegseekWrapper(BaseToolWrapper):
    name = "stegseek"
    display_name = "Stegseek"
    category = ToolCategory.CRYPTO
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["stegseek"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        output = kwargs.get("output", "/tmp/stegseek_out.txt")
        return ["stegseek", target, wordlist, output]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        if "found" in output.lower() or "passphrase" in output.lower():
            findings.append(ToolFinding(
                tool=self.name,
                title="Steganografie-wachtwoord gekraakt",
                detail=output[:500],
                severity=Severity.HIGH,
                recommendation="Gebruik sterke wachtwoorden voor steganografie.",
            ))
        return findings
