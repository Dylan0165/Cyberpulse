"""Objdump — binary disassembler/header analysis."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ObjdumpWrapper(BaseToolWrapper):
    name = "objdump"
    display_name = "Objdump"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["objdump"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=10)

    def build_command(self, target: str, **kwargs) -> list[str]:
        mode = kwargs.get("mode", "headers")
        if mode == "disassemble":
            return ["objdump", "-d", "-M", "intel", target]
        return ["objdump", "-x", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        lower = stdout.lower()
        if "stack_chk_fail" not in lower and "canary" not in lower:
            findings.append(ToolFinding(
                tool=self.name,
                title="Geen stack protector gedetecteerd",
                detail="__stack_chk_fail niet gevonden in symbolen.",
                severity=Severity.MEDIUM,
                recommendation="Compileer met -fstack-protector-all.",
            ))
        dangerous_funcs = re.findall(r'<(gets|strcpy|strcat|sprintf|scanf)@plt>', stdout)
        if dangerous_funcs:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Onveilige functies: {', '.join(set(dangerous_funcs))}",
                detail=f"Gevonden: {', '.join(set(dangerous_funcs))}",
                severity=Severity.HIGH,
                recommendation="Vervang door veilige varianten (fgets, strncpy, snprintf).",
            ))
        return findings
