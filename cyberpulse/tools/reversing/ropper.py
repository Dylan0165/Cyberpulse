"""ROPgadget / Ropper — ROP gadget finder."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class RopperWrapper(BaseToolWrapper):
    name = "ropper"
    display_name = "Ropper"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["ropper"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return ["ropper", "--file", target, "--search", "pop|ret|syscall|int"]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        gadgets = [l.strip() for l in stdout.splitlines() if "0x" in l]
        if gadgets:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Ropper: {len(gadgets)} ROP gadgets gevonden",
                detail="\n".join(gadgets[:20]),
                severity=Severity.MEDIUM,
                recommendation="Activeer ASLR, PIE en CFI om ROP-aanvallen te bemoeilijken.",
            ))
        return findings
