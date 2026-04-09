"""Strace — system call tracer."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class StraceWrapper(BaseToolWrapper):
    name = "strace"
    display_name = "Strace"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["strace"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=10)

    def build_command(self, target: str, **kwargs) -> list[str]:
        pid = kwargs.get("pid")
        if pid:
            return ["strace", "-p", str(pid), "-c", "-S", "calls"]
        return ["strace", "-f", "-c", target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        # strace output goes to stderr
        output = stderr or stdout
        # Look for sensitive syscalls
        sensitive = {"connect", "bind", "execve", "open", "openat", "ptrace"}
        found_sensitive = set()
        for line in output.splitlines():
            for sc in sensitive:
                if sc in line:
                    found_sensitive.add(sc)
        if found_sensitive:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Gevoelige syscalls: {', '.join(sorted(found_sensitive))}",
                detail=output[:2000],
                severity=Severity.INFO,
                recommendation="Controleer of syscalls verwacht zijn voor deze applicatie.",
            ))
        return findings
