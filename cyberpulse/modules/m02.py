"""Module 02 — Service Fingerprinting.

Identifies service versions on open ports via banner grabbing and protocol probes.
"""

import json
import logging
import socket
import ssl
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m02")

# Protocol probes: send bytes, parse response
PROBES = {
    "HTTP": {
        "ports": [80, 8080, 8888, 9090],
        "send": b"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n",
        "parse": "_parse_http",
    },
    "HTTPS": {
        "ports": [443, 8443],
        "send": b"HEAD / HTTP/1.1\r\nHost: {target}\r\nConnection: close\r\n\r\n",
        "parse": "_parse_http",
        "tls": True,
    },
    "SSH": {
        "ports": [22],
        "send": b"",
        "parse": "_parse_ssh",
    },
    "SMTP": {
        "ports": [25, 465, 587],
        "send": b"EHLO cyberpulse\r\n",
        "parse": "_parse_smtp",
    },
    "FTP": {
        "ports": [21],
        "send": b"",
        "parse": "_parse_ftp",
    },
}


class Scanner:
    name = "Service Fingerprinting"
    phase = "reconnaissance"
    description = "Identifies service versions and technologies via banner grabbing"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("fingerprint_timeout", 3)

    def run(self) -> dict:
        findings = []
        raw_lines = []

        # Load open ports from port scan if available
        port_scan_file = self.output_dir / "01_port_scan.json"
        open_ports = set()
        if port_scan_file.exists():
            with open(port_scan_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                open_ports = set(data.get("open_ports", []))
            raw_lines.append(f"Loaded {len(open_ports)} open ports from port scan")
        else:
            # Default test ports
            open_ports = {21, 22, 25, 80, 443, 8080}
            raw_lines.append("No port scan data, using default ports")

        try:
            ip = socket.gethostbyname(self.target)
        except socket.gaierror:
            ip = self.target

        for port in sorted(open_ports):
            banner = self._grab_banner(ip, port)
            if banner:
                finding = {
                    "type": "service_version",
                    "port": port,
                    "banner": banner[:500],
                    "severity": "info",
                }

                # Check for outdated/vulnerable version hints
                lower = banner.lower()
                for keyword in ["apache/2.2", "openssl/1.0", "php/5.", "nginx/1.1", "vsftpd 2.3.4"]:
                    if keyword in lower:
                        finding["severity"] = "high"
                        finding["note"] = f"Potentially outdated: {keyword}"
                        break

                findings.append(finding)
                raw_lines.append(f"  {port}: {banner[:120]}")
            else:
                raw_lines.append(f"  {port}: no banner")

        # Protocol-specific probes
        for proto_name, probe in PROBES.items():
            for port in probe["ports"]:
                if port not in open_ports:
                    continue
                result = self._probe(ip, port, probe)
                if result:
                    findings.append(result)
                    raw_lines.append(f"  {proto_name}@{port}: {result.get('detail', '')[:80]}")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "02_fingerprint.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Fingerprinting %s: %d services identified", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _grab_banner(self, ip: str, port: int) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((ip, port))
                # Some services send banner on connect
                try:
                    s.settimeout(2)
                    data = s.recv(1024)
                    return data.decode("utf-8", errors="replace").strip()
                except socket.timeout:
                    return ""
        except Exception:
            return ""

    def _probe(self, ip: str, port: int, probe: dict) -> dict | None:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(self.timeout)
                s.connect((ip, port))

                if probe.get("tls"):
                    ctx = ssl.create_default_context()
                    ctx.check_hostname = False
                    ctx.verify_mode = ssl.CERT_NONE
                    s = ctx.wrap_socket(s, server_hostname=self.target)

                payload = probe["send"].replace(b"{target}", self.target.encode())
                if payload:
                    s.sendall(payload)

                s.settimeout(3)
                response = s.recv(4096).decode("utf-8", errors="replace")

                parser = getattr(self, probe["parse"], None)
                if parser:
                    return parser(port, response)
        except Exception:
            pass
        return None

    @staticmethod
    def _parse_http(port: int, response: str) -> dict | None:
        if not response:
            return None
        headers = {}
        for line in response.split("\r\n"):
            if ":" in line:
                k, v = line.split(":", 1)
                headers[k.strip().lower()] = v.strip()
        server = headers.get("server", "")
        powered = headers.get("x-powered-by", "")
        return {
            "type": "http_fingerprint",
            "port": port,
            "server": server,
            "x_powered_by": powered,
            "detail": f"Server: {server}, X-Powered-By: {powered}".strip(", "),
            "severity": "info",
        }

    @staticmethod
    def _parse_ssh(port: int, response: str) -> dict | None:
        if not response:
            return None
        return {
            "type": "ssh_fingerprint",
            "port": port,
            "detail": response.split("\n")[0][:200],
            "severity": "info",
        }

    @staticmethod
    def _parse_smtp(port: int, response: str) -> dict | None:
        if not response:
            return None
        return {
            "type": "smtp_fingerprint",
            "port": port,
            "detail": response.split("\n")[0][:200],
            "severity": "info",
        }

    @staticmethod
    def _parse_ftp(port: int, response: str) -> dict | None:
        if not response:
            return None
        return {
            "type": "ftp_fingerprint",
            "port": port,
            "detail": response.split("\n")[0][:200],
            "severity": "info",
        }
