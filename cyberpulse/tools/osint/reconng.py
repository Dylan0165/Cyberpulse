"""Recon-ng — web reconnaissance framework."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ReconNgWrapper(BaseToolWrapper):
    name = "recon-ng"
    display_name = "Recon-ng"
    category = ToolCategory.OSINT
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["recon-ng"]
    default_timeout = 180
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=90)

    def build_command(self, target: str, **kwargs) -> list[str]:
        workspace = kwargs.get("workspace", "cyberpulse")
        commands = (
            f"workspaces create {workspace}; "
            f"db insert domains domain={target}; "
            f"modules load recon/domains-hosts/hackertarget; run; "
            f"show hosts; exit"
        )
        return ["recon-ng", "-C", commands]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        hosts = set()
        capture = False
        for line in stdout.splitlines():
            if "host" in line.lower() and "ip_address" in line.lower():
                capture = True
                continue
            if capture and line.strip() and not line.startswith("+") and not line.startswith("-"):
                parts = [p.strip() for p in line.split("|") if p.strip()]
                if parts:
                    hosts.add(parts[0])
        if hosts:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Recon-ng: {len(hosts)} hosts gevonden",
                detail="\n".join(sorted(hosts)[:50]),
                severity=Severity.INFO,
                recommendation="Valideer ontdekte hosts en controleer scope.",
            ))
        return findings
