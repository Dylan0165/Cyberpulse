"""Scapy — Python-native packet crafting and analysis."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class ScapyWrapper(BaseToolWrapper):
    name = "scapy"
    display_name = "Scapy"
    category = ToolCategory.NETWORK_SCANNING
    implementation = ImplementationMethod.PYTHON_NATIVE
    python_dependencies = ["scapy"]
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=30)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return []

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        return []

    def run_native(self, target: str, output_dir=None, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            from scapy.all import sr1, IP, ICMP, TCP
            import socket

            # ICMP ping
            pkt = sr1(IP(dst=target)/ICMP(), timeout=3, verbose=0)
            if pkt:
                ttl = pkt.ttl
                os_guess = "Linux/Unix" if ttl <= 64 else "Windows" if ttl <= 128 else "Onbekend"
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Host bereikbaar (TTL={ttl}, vermoedelijk {os_guess})",
                    detail=f"ICMP ping succesvol, TTL={ttl}",
                    severity=Severity.INFO,
                    description=f"Het target reageert op ICMP. TTL={ttl} suggereert {os_guess}.",
                ))

            # Quick TCP SYN check on common ports
            common_ports = [22, 80, 443, 8080]
            for port in common_ports:
                pkt = sr1(IP(dst=target)/TCP(dport=port, flags="S"), timeout=2, verbose=0)
                if pkt and pkt.haslayer(TCP) and pkt[TCP].flags == 0x12:  # SYN-ACK
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"Poort {port} open",
                        detail=f"Scapy SYN scan: poort {port} is open",
                        severity=Severity.INFO, port=port,
                    ))

        except ImportError:
            pass
        except Exception as e:
            findings.append(ToolFinding(
                tool=self.name, title="Scapy scan mislukt",
                detail=str(e), severity=Severity.INFO,
            ))
        return findings
