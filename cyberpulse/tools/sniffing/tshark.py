"""TShark — Wireshark CLI packet capture and analysis."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

INSECURE_PROTOCOLS = {"ftp", "telnet", "http", "pop", "imap", "smtp"}


@register
class TsharkWrapper(BaseToolWrapper):
    name = "tshark"
    display_name = "TShark (Wireshark CLI)"
    category = ToolCategory.SNIFFING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["tshark"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        interface = kwargs.get("interface", "")
        packet_count = kwargs.get("packet_count", "100")
        capture_filter = kwargs.get("capture_filter", f"host {target}")
        pcap_file = kwargs.get("pcap_file", "")

        if pcap_file:
            return ["tshark", "-r", str(pcap_file), "-T", "fields",
                    "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst",
                    "-e", "tcp.dstport", "-e", "_ws.col.Protocol", "-e", "_ws.col.Info",
                    "-c", str(packet_count)]

        cmd = ["tshark", "-c", str(packet_count), "-T", "fields",
               "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst",
               "-e", "tcp.dstport", "-e", "_ws.col.Protocol", "-e", "_ws.col.Info"]

        if interface:
            cmd.extend(["-i", interface])
        if capture_filter:
            cmd.extend(["-f", capture_filter])

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        protocols_seen = set()

        for line in stdout.splitlines():
            parts = line.strip().split("\t")
            if len(parts) >= 5:
                proto = parts[4].lower().strip()
                if proto in INSECURE_PROTOCOLS and proto not in protocols_seen:
                    protocols_seen.add(proto)
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"Onversleuteld protocol gedetecteerd: {proto.upper()}",
                        detail=f"TShark detecteerde {proto.upper()} verkeer",
                        severity=Severity.MEDIUM if proto in ("http",) else Severity.HIGH,
                        description=f"Er is {proto.upper()} verkeer gedetecteerd. "
                                    "Dit protocol verstuurt data onversleuteld.",
                        recommendation=f"Gebruik de versleutelde variant van {proto.upper()} "
                                       "(bijv. HTTPS, SFTP, IMAPS).",
                        raw_output=line[:500],
                    ))

        return findings
