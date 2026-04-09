"""Hydra — brute-force network login cracker."""

import re
from pathlib import Path

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class HydraWrapper(BaseToolWrapper):
    name = "hydra"
    display_name = "Hydra"
    category = ToolCategory.PASSWORD_CRACKING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["hydra"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        service = kwargs.get("service", "ssh")
        userlist = kwargs.get("userlist", "")
        passlist = kwargs.get("passlist", "")
        username = kwargs.get("username", "")
        password = kwargs.get("password", "")
        port = kwargs.get("port", "")
        threads = kwargs.get("threads", "4")

        cmd = ["hydra"]

        if userlist:
            cmd.extend(["-L", str(userlist)])
        elif username:
            cmd.extend(["-l", username])
        else:
            cmd.extend(["-l", "admin"])

        if passlist:
            cmd.extend(["-P", str(passlist)])
        elif password:
            cmd.extend(["-p", password])

        cmd.extend(["-t", str(threads), "-f"])  # -f = stop on first success

        if port:
            cmd.extend(["-s", str(port)])

        cmd.extend([target, service])
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr
        service = kwargs.get("service", "ssh")

        # Parse successful logins: "[22][ssh] host: x login: y password: z"
        pattern = r"\[(\d+)\]\[(\w+)\]\s+host:\s+(\S+)\s+login:\s+(\S+)\s+password:\s+(\S+)"
        for match in re.finditer(pattern, combined):
            port, svc, host, login, passwd = match.groups()
            is_default = login.lower() in ("admin", "root", "administrator", "test", "guest")
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Login succesvol: {login}@{svc}:{port}",
                detail=f"Hydra heeft credentials gevonden voor {svc} op poort {port}",
                severity=Severity.CRITICAL if is_default else Severity.HIGH,
                description=f"Brute-force aanval op {svc} service was succesvol. "
                            f"Gebruiker '{login}' heeft een zwak of standaard wachtwoord.",
                recommendation=f"Verander het wachtwoord van '{login}' onmiddellijk. "
                               "Activeer account lockout na 5 mislukte pogingen. "
                               "Overweeg MFA voor remote toegang.",
                port=int(port),
                service=svc,
                raw_output=match.group(0),
                references=["https://owasp.org/www-community/attacks/Brute_force_attack"],
            ))

        # Check for "valid password found" without the detailed format
        if not findings and "successfully completed" in combined.lower():
            valid = re.findall(r"(\d+)\s+valid\s+password", combined, re.IGNORECASE)
            if valid and int(valid[0]) > 0:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"{valid[0]} geldige wachtwoorden gevonden",
                    detail="Hydra vond geldige credentials",
                    severity=Severity.HIGH,
                    description="Hydra heeft succesvolle logins gevonden via brute-force.",
                    recommendation="Controleer de Hydra output voor details en wijzig alle getroffen wachtwoorden.",
                    raw_output=combined[:500],
                ))

        return findings
