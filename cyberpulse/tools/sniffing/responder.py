"""Responder — LLMNR/NBT-NS/mDNS poisoner (analysis mode)."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ResponderWrapper(BaseToolWrapper):
    name = "responder"
    display_name = "Responder"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["responder"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "eth0")
        return ["responder", "-I", interface, "-A"]  # -A = Analyze mode only

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        # NTLM hashes captured
        ntlm_hashes = re.findall(r"NTLMv[12]-SSP.*?:.*?:.*", combined)
        if ntlm_hashes:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(ntlm_hashes)} NTLM hashes gecaptured",
                detail="Responder heeft NTLM hashes onderschept",
                severity=Severity.HIGH,
                description=f"Responder (analyse modus) heeft {len(ntlm_hashes)} NTLM hashes gezien. "
                            "LLMNR/NBT-NS is actief op het netwerk.",
                recommendation="Schakel LLMNR en NBT-NS uit via Group Policy. Implementeer SMB signing.",
            ))

        # LLMNR/NBT-NS queries seen
        if "LLMNR" in combined or "NBT-NS" in combined:
            findings.append(ToolFinding(
                tool=self.name,
                title="LLMNR/NBT-NS verkeer gedetecteerd",
                detail="Het netwerk gebruikt onveilige name resolution protocols",
                severity=Severity.MEDIUM,
                description="LLMNR en/of NBT-NS zijn actief. Een aanvaller kan deze protocollen misbruiken "
                            "om credentials te onderscheppen.",
                recommendation="Schakel LLMNR uit (GPO: Computer Configuration > Administrative Templates > Network > DNS Client). "
                               "Schakel NBT-NS uit op alle netwerkinterfaces.",
            ))

        return findings
