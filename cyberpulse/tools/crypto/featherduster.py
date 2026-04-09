"""FeatherDuster — crypto analysis framework (Python native)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class FeatherDusterWrapper(BaseToolWrapper):
    name = "featherduster"
    display_name = "FeatherDuster"
    category = ToolCategory.CRYPTO
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["featherduster"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["featherduster", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        output = stdout + stderr
        lower = output.lower()
        if "weak" in lower or "vulnerable" in lower or "broken" in lower:
            findings.append(ToolFinding(
                tool=self.name,
                title="Zwakke cryptografie gedetecteerd",
                detail=output[:2000],
                severity=Severity.HIGH,
                recommendation="Vervang zwakke cryptografische implementatie.",
            ))
        elif output.strip():
            findings.append(ToolFinding(
                tool=self.name,
                title="FeatherDuster analyse",
                detail=output[:2000],
                severity=Severity.INFO,
                recommendation="Bekijk cryptoanalyse resultaten.",
            ))
        return findings
