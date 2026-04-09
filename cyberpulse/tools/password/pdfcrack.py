"""PDFCrack — PDF password recovery."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class PdfcrackWrapper(BaseToolWrapper):
    name = "pdfcrack"
    display_name = "PDFCrack"
    category = ToolCategory.PASSWORD
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["pdfcrack"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=60)

    def build_command(self, target: str, **kwargs) -> list[str]:
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/rockyou.txt")
        return ["pdfcrack", "-f", target, "-w", wordlist]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in (stdout + stderr).splitlines():
            if "found" in line.lower() and "password" in line.lower():
                findings.append(ToolFinding(
                    tool=self.name,
                    title="PDF-wachtwoord gekraakt",
                    detail=line.strip(),
                    severity=Severity.CRITICAL,
                    recommendation="Gebruik een sterk wachtwoord voor PDF-encryptie.",
                ))
        return findings
