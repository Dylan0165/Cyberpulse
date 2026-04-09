"""Radare2 — reverse engineering framework."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class Radare2Wrapper(BaseToolWrapper):
    name = "radare2"
    display_name = "Radare2"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["r2"]
    default_timeout = 120
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        commands = kwargs.get("r2_commands", "aaa;aflj;iIj")
        return ["r2", "-q", "-c", commands, target]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        # Try JSON function list
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, list):
                    dangerous = [f for f in data if isinstance(f, dict) and f.get("name", "") in ("sym.system", "sym.exec", "sym.popen", "sym.gets", "sym.strcpy")]
                    if dangerous:
                        findings.append(ToolFinding(
                            tool=self.name,
                            title=f"Onveilige functies: {len(dangerous)}",
                            detail="\n".join(f["name"] for f in dangerous),
                            severity=Severity.HIGH,
                            recommendation="Gebruik veilige alternatieven voor gevaarlijke C-functies.",
                        ))
                elif isinstance(data, dict):
                    info = data
                    if not info.get("canary", True):
                        findings.append(ToolFinding(
                            tool=self.name,
                            title="Geen stack canary",
                            detail="Binary heeft geen stack canary protectie.",
                            severity=Severity.HIGH,
                            recommendation="Compileer met -fstack-protector.",
                        ))
                    if not info.get("nx", True):
                        findings.append(ToolFinding(
                            tool=self.name,
                            title="NX bit niet ingeschakeld",
                            detail="Executable stack — code execution mogelijk.",
                            severity=Severity.HIGH,
                            recommendation="Compileer met NX/DEP ingeschakeld.",
                        ))
                    if not info.get("pic", False):
                        findings.append(ToolFinding(
                            tool=self.name,
                            title="Geen PIE/ASLR",
                            detail="Binary is niet position-independent.",
                            severity=Severity.MEDIUM,
                            recommendation="Compileer met -fPIE -pie voor ASLR.",
                        ))
            except (json.JSONDecodeError, TypeError):
                continue
        return findings
