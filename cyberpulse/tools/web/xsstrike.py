"""XSStrike — advanced XSS detection tool."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class XsstrikeWrapper(BaseToolWrapper):
    name = "xsstrike"
    display_name = "XSStrike"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["xsstrike"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        crawl = kwargs.get("crawl", False)
        cmd = ["xsstrike", "--url", url]
        if crawl:
            cmd.append("--crawl")
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        # Look for confirmed XSS
        if "Vulnerable" in combined or "XSS" in combined:
            for line in combined.splitlines():
                if "vulnerable" in line.lower() or "xss" in line.lower():
                    findings.append(ToolFinding(
                        tool=self.name,
                        title="XSS kwetsbaarheid gevonden",
                        detail=line.strip()[:200],
                        severity=Severity.HIGH,
                        description="XSStrike heeft een Cross-Site Scripting kwetsbaarheid gevonden.",
                        recommendation="Implementeer output encoding en Content Security Policy (CSP).",
                        references=["https://owasp.org/www-community/attacks/xss/"],
                        raw_output=line.strip()[:500],
                    ))

        # Reflected params
        for match in re.finditer(r"Reflections found:\s*(\d+)", combined):
            count = int(match.group(1))
            if count > 0:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"{count} reflecties gevonden",
                    detail="Parameters worden gereflecteerd in de response",
                    severity=Severity.MEDIUM,
                    description="XSStrike detecteerde gereflecteerde input. Dit kan leiden tot XSS.",
                    recommendation="Valideer en encode alle user input.",
                ))

        return findings
