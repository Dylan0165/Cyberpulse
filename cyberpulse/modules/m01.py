"""Module 01 — Port Scanner.

Scans the target for open TCP ports using python-nmap (if available)
or a pure-Python fallback with socket connections.
"""

import json
import logging
import socket
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m01")

# Common ports to scan
COMMON_PORTS = [
    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 465,
    587, 636, 993, 995, 1433, 1521, 2049, 3306, 3389, 5432, 5900,
    6379, 8080, 8443, 8888, 9090, 9200, 27017,
]

SERVICE_MAP = {
    21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 111: "RPC", 135: "MSRPC", 139: "NetBIOS",
    143: "IMAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS", 587: "SMTP-Submit",
    636: "LDAPS", 993: "IMAPS", 995: "POP3S", 1433: "MSSQL", 1521: "Oracle",
    2049: "NFS", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL",
    5900: "VNC", 6379: "Redis", 8080: "HTTP-Alt", 8443: "HTTPS-Alt",
    8888: "HTTP-Alt", 9090: "Web-Admin", 9200: "Elasticsearch", 27017: "MongoDB",
}


class Scanner:
    name = "Port Scanner"
    phase = "reconnaissance"
    description = "Scans for open TCP ports and identifies running services"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("port_scan_timeout", 2)

    def run(self) -> dict:
        findings = []
        raw_lines = []
        open_ports = []

        # Resolve target to IP
        try:
            ip = socket.gethostbyname(self.target)
            raw_lines.append(f"Resolved {self.target} -> {ip}")
        except socket.gaierror:
            ip = self.target
            raw_lines.append(f"Could not resolve hostname, using {ip} directly")

        # Try nmap first
        nmap_used = False
        try:
            import nmap
            nm = nmap.PortScanner()
            port_str = ",".join(str(p) for p in COMMON_PORTS)
            raw_lines.append(f"Scanning {ip} with nmap on ports: {port_str}")
            nm.scan(ip, port_str, arguments="-sV -T4 --open")

            for host in nm.all_hosts():
                for proto in nm[host].all_protocols():
                    for port in sorted(nm[host][proto].keys()):
                        state = nm[host][proto][port]["state"]
                        service = nm[host][proto][port].get("name", "unknown")
                        version = nm[host][proto][port].get("version", "")
                        product = nm[host][proto][port].get("product", "")

                        if state == "open":
                            open_ports.append(port)
                            svc_info = f"{product} {version}".strip() or service
                            raw_lines.append(f"  {port}/{proto} open {svc_info}")
                            finding = {
                                "type": "open_port",
                                "port": port,
                                "protocol": proto,
                                "service": service,
                                "product": product,
                                "version": version,
                                "state": state,
                                "severity": self._port_severity(port, service),
                            }
                            findings.append(finding)
            nmap_used = True
        except (ImportError, Exception) as e:
            raw_lines.append(f"nmap not available ({e}), falling back to socket scan")

        # Socket fallback
        if not nmap_used:
            raw_lines.append(f"Socket scan on {ip} ({len(COMMON_PORTS)} ports, timeout={self.timeout}s)")
            for port in COMMON_PORTS:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(self.timeout)
                        result = s.connect_ex((ip, port))
                        if result == 0:
                            service = SERVICE_MAP.get(port, "unknown")
                            open_ports.append(port)
                            raw_lines.append(f"  {port}/tcp open {service}")

                            # Try banner grab
                            banner = ""
                            try:
                                s.settimeout(1)
                                s.sendall(b"\r\n")
                                banner = s.recv(1024).decode("utf-8", errors="replace").strip()
                            except Exception:
                                pass

                            findings.append({
                                "type": "open_port",
                                "port": port,
                                "protocol": "tcp",
                                "service": service,
                                "banner": banner[:200] if banner else "",
                                "severity": self._port_severity(port, service),
                            })
                except Exception:
                    pass

        raw_lines.append(f"\nTotal open ports: {len(open_ports)}")
        raw_output = "\n".join(raw_lines)

        # Save output
        outfile = self.output_dir / "01_port_scan.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "open_ports": open_ports}, f, indent=2)

        logger.info("Port scan on %s: %d open ports found", self.target, len(open_ports))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _port_severity(port: int, service: str) -> str:
        high_risk = {21, 23, 135, 139, 445, 1433, 3389, 5900, 6379, 27017}
        medium_risk = {25, 110, 111, 143, 3306, 5432, 9200}
        if port in high_risk:
            return "high"
        if port in medium_risk:
            return "medium"
        return "info"
