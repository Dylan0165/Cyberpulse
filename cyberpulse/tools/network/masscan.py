"""Masscan — fastest port scanner with rate limiting for laptop use."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

# Ports commonly associated with higher risk
HIGH_RISK_PORTS = {21, 23, 445, 1433, 1521, 3306, 3389, 5432, 5900, 6379, 27017}
MEDIUM_RISK_PORTS = {25, 110, 135, 139, 143, 161, 389, 636, 993, 995, 8080, 8443, 9200}


@register
class MasscanWrapper(BaseToolWrapper):
    name = "masscan"
    display_name = "Masscan"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["masscan"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=120)

    def build_command(self, target: str, **kwargs) -> list[str]:
        ports = kwargs.get("ports", "0-65535")
        rate = kwargs.get("rate", "1000")  # Safe laptop default

        if self._laptop_mode:
            rate = str(min(int(rate), 1000))

        cmd = [
            "masscan", target,
            "-p", str(ports),
            "--rate", str(rate),
            "--open-only",
            "-oL", "-",  # List output to stdout
        ]
        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: "open tcp 80 192.168.1.1 timestamp"
            match = re.match(r"open\s+(tcp|udp)\s+(\d+)\s+(\S+)", line)
            if match:
                proto, port_str, ip = match.groups()
                port = int(port_str)

                if port in HIGH_RISK_PORTS:
                    sev = Severity.HIGH
                elif port in MEDIUM_RISK_PORTS:
                    sev = Severity.MEDIUM
                else:
                    sev = Severity.INFO

                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Open poort {port}/{proto} op {ip}",
                    detail=f"Masscan detecteerde open poort {port}/{proto}",
                    severity=sev,
                    port=port,
                    service=proto,
                    description=f"Poort {port}/{proto} is open op {ip}.",
                    recommendation="Controleer of deze poort nodig is. Sluit onnodige poorten.",
                    raw_output=line,
                ))

        return findings
