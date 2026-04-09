"""Amass — advanced subdomain enumeration."""

import json as json_mod
import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class AmassWrapper(BaseToolWrapper):
    name = "amass"
    display_name = "Amass"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["amass"]
    default_timeout = 600
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=300)

    def build_command(self, target: str, **kwargs) -> list[str]:
        domain = target.replace("http://", "").replace("https://", "").split("/")[0]
        passive = kwargs.get("passive", True)

        cmd = ["amass", "enum", "-d", domain, "-json", "-"]

        if passive:
            cmd.append("-passive")

        if self._laptop_mode:
            cmd.extend(["-timeout", "5"])  # 5 minute limit

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        subdomains = set()

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                data = json_mod.loads(line)
                name = data.get("name", "")
                if name:
                    subdomains.add(name)
            except json_mod.JSONDecodeError:
                # Plain text output
                if "." in line and " " not in line:
                    subdomains.add(line)

        if subdomains:
            sensitive = [s for s in subdomains if any(
                k in s.lower() for k in ("admin", "staging", "dev", "test", "backup", "vpn", "internal", "db", "api")
            )]

            findings.append(ToolFinding(
                tool=self.name,
                title=f"{len(subdomains)} subdomains gevonden",
                detail=f"Amass enumeratie vond {len(subdomains)} subdomains",
                severity=Severity.MEDIUM if sensitive else Severity.LOW,
                description=f"Amass heeft {len(subdomains)} subdomains gevonden voor het target. " +
                            (f"Waarvan {len(sensitive)} mogelijk gevoelig: {', '.join(sensitive[:5])}" if sensitive else ""),
                recommendation="Controleer alle subdomains op kwetsbaarheden. "
                               "Verwijder ongebruikte subdomains.",
                raw_output="\n".join(sorted(subdomains)[:50]),
            ))

            for sd in sensitive[:5]:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Gevoelig subdomain: {sd}",
                    detail=f"Potentieel gevoelig subdomain gevonden",
                    severity=Severity.MEDIUM,
                    description=f"Het subdomain '{sd}' suggereert een gevoelige service.",
                    recommendation=f"Controleer of '{sd}' beveiligd en noodzakelijk is.",
                ))

        return findings
