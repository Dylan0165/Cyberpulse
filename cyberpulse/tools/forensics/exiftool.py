"""Exiftool — metadata extraction from files."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

_SENSITIVE_TAGS = {"gpslatitude", "gpslongitude", "author", "creator", "email", "username", "password"}


@register
class ExiftoolWrapper(BaseToolWrapper):
    name = "exiftool"
    display_name = "ExifTool"
    category = ToolCategory.FORENSICS
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["exiftool"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=5)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["exiftool", "-j", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            if isinstance(data, list) and data:
                meta = data[0]
                sensitive = {k: v for k, v in meta.items() if k.lower().replace(" ", "") in _SENSITIVE_TAGS and v}
                if sensitive:
                    findings.append(ToolFinding(
                        tool=self.name,
                        title="Gevoelige metadata gevonden",
                        detail="\n".join(f"{k}: {v}" for k, v in sensitive.items()),
                        severity=Severity.MEDIUM,
                        recommendation="Verwijder gevoelige metadata voor publicatie.",
                    ))
                else:
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"ExifTool: {len(meta)} metadata velden",
                        detail=json.dumps(meta, indent=2)[:2000],
                        severity=Severity.INFO,
                        recommendation="Controleer metadata op ongewenste informatie.",
                    ))
        except (json.JSONDecodeError, TypeError):
            pass
        return findings
