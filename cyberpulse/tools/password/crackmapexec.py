"""CrackMapExec — Windows/AD post-exploitation tool."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class CrackMapExecWrapper(BaseToolWrapper):
    name = "crackmapexec"
    display_name = "CrackMapExec"
    category = ToolCategory.PASSWORD_CRACKING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["crackmapexec"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        protocol = kwargs.get("protocol", "smb")
        username = kwargs.get("username", "")
        password = kwargs.get("password", "")
        userlist = kwargs.get("userlist", "")
        passlist = kwargs.get("passlist", "")

        cmd = ["crackmapexec", protocol, target]

        if userlist:
            cmd.extend(["-u", str(userlist)])
        elif username:
            cmd.extend(["-u", username])

        if passlist:
            cmd.extend(["-p", str(passlist)])
        elif password:
            cmd.extend(["-p", password])

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        for line in combined.splitlines():
            # Successful auth: [+] or (Pwn3d!)
            if "[+]" in line or "Pwn3d!" in line:
                is_admin = "Pwn3d!" in line
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Admin toegang via SMB" if is_admin else "Geldige credentials gevonden",
                    detail=line.strip(),
                    severity=Severity.CRITICAL if is_admin else Severity.HIGH,
                    description="CrackMapExec heeft geldige credentials gevonden. " +
                                ("De gebruiker heeft administrator rechten!" if is_admin else ""),
                    recommendation="Wijzig wachtwoorden, beperk SMB toegang, activeer MFA.",
                    raw_output=line.strip()[:500],
                ))

            # Shares enumerated
            if "READ" in line or "WRITE" in line:
                writable = "WRITE" in line
                share_match = re.search(r"\s+(\S+)\s+(READ|WRITE)", line)
                if share_match:
                    share_name = share_match.group(1)
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"SMB Share: {share_name} ({'schrijfbaar' if writable else 'leesbaar'})",
                        detail=line.strip(),
                        severity=Severity.HIGH if writable else Severity.MEDIUM,
                        description=f"SMB share '{share_name}' is {'schrijfbaar' if writable else 'leesbaar'}.",
                        recommendation="Beperk share permissies. Verwijder onnodige shares.",
                    ))

        return findings
