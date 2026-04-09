"""Strings — extract printable strings from binary files."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_INTERESTING_PATTERNS = [
    (re.compile(r'https?://\S+'), "URL gevonden"),
    (re.compile(r'password\s*[:=]', re.I), "Wachtwoord referentie"),
    (re.compile(r'api[_-]?key\s*[:=]', re.I), "API key referentie"),
    (re.compile(r'eyJ[A-Za-z0-9_-]+\.eyJ'), "JWT token"),
    (re.compile(r'[A-Za-z0-9+/]{40,}={0,2}'), "Base64 string"),
]


@register
class StringsWrapper(BaseToolWrapper):
    name = "strings"
    display_name = "Strings"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["strings"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=5)

    def build_command(self, target: str, **kwargs) -> list[str]:
        min_len = kwargs.get("min_length", "8")
        return ["strings", "-n", str(min_len), target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for pat, label in _INTERESTING_PATTERNS:
            matches = pat.findall(stdout)
            if matches:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Strings: {label} ({len(matches)}x)",
                    detail="\n".join(matches[:10]),
                    severity=Severity.MEDIUM if "password" in label.lower() or "key" in label.lower() else Severity.LOW,
                    recommendation="Controleer gevonden strings op hardcoded credentials.",
                ))
        return findings
