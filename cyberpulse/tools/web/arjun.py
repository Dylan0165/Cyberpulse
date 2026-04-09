"""Arjun — HTTP parameter discovery (Python native)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ArjunWrapper(BaseToolWrapper):
    name = "arjun"
    display_name = "Arjun"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["arjun"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        return ["arjun", "-u", url, "--stable"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        params = []
        for line in combined.splitlines():
            line = line.strip()
            if line and not line.startswith("[") and not line.startswith("http"):
                # Arjun outputs parameter names
                if len(line) < 50 and " " not in line:
                    params.append(line)

        if params:
            sensitive = [p for p in params if any(
                k in p.lower() for k in ("pass", "token", "key", "secret", "auth", "admin", "debug", "id", "user")
            )]
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(params)} verborgen parameters gevonden",
                detail=f"Parameters: {', '.join(params[:10])}",
                severity=Severity.MEDIUM if sensitive else Severity.LOW,
                description=f"Arjun heeft {len(params)} verborgen HTTP parameters ontdekt. " +
                            (f"Gevoelige params: {', '.join(sensitive)}" if sensitive else ""),
                recommendation="Test gevonden parameters op injection kwetsbaarheden.",
                raw_output="\n".join(params[:20]),
            ))

        return findings
