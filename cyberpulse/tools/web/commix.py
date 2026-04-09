"""Commix — command injection exploitation tool."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class CommixWrapper(BaseToolWrapper):
    name = "commix"
    display_name = "Commix"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["commix"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        return ["commix", "--url", url, "--all", "--batch"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        if "is vulnerable" in combined.lower():
            # Extract technique
            technique = "classic"
            for t in ["eval-based", "time-based", "file-based"]:
                if t in combined.lower():
                    technique = t
                    break

            param_match = re.search(r"Parameter '(\S+)'", combined)
            param = param_match.group(1) if param_match else "onbekend"

            findings.append(ToolFinding(
                tool=self.name,
                title=f"Command Injection in '{param}' ({technique})",
                detail=f"Commix bevestigde {technique} command injection",
                severity=Severity.CRITICAL,
                description=f"Commix heeft een {technique} command injection gevonden in parameter '{param}'. "
                            "Dit geeft een aanvaller directe shell toegang tot de server.",
                recommendation="Gebruik parameterized commands, vermijd shell execution. "
                               "Implementeer strikte input validatie.",
                references=["https://owasp.org/www-community/attacks/Command_Injection"],
                raw_output=combined[:1000],
            ))

        return findings
