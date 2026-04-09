"""Module 47 — Network Service Security Testing.

Scans for exposed network services, tests encryption strength,
and checks for known service vulnerabilities.
"""

import json
import logging
import re
import socket
import ssl
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m47")

# Extended port list for network service discovery
SERVICE_PORTS = [
    (21, "FTP"), (22, "SSH"), (23, "Telnet"), (25, "SMTP"),
    (53, "DNS"), (80, "HTTP"), (110, "POP3"), (111, "RPCbind"),
    (135, "MS-RPC"), (139, "NetBIOS"), (143, "IMAP"),
    (161, "SNMP"), (389, "LDAP"), (443, "HTTPS"),
    (445, "SMB"), (465, "SMTPS"), (587, "SMTP Submission"),
    (636, "LDAPS"), (993, "IMAPS"), (995, "POP3S"),
    (1433, "MSSQL"), (1521, "Oracle"), (2049, "NFS"),
    (2082, "cPanel"), (2083, "cPanel SSL"), (2222, "SSH-alt"),
    (3306, "MySQL"), (3389, "RDP"), (5432, "PostgreSQL"),
    (5900, "VNC"), (5985, "WinRM"), (6379, "Redis"),
    (8080, "HTTP-Alt"), (8443, "HTTPS-Alt"), (8888, "HTTP-Alt2"),
    (9090, "HTTP-Alt3"), (9200, "Elasticsearch"), (27017, "MongoDB"),
]


class Scanner:
    name = "Network Service Security"
    phase = "scanning"
    description = "Scans network services, checks encryption, and detects service vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Network service security scan for {self.target}"]

        try:
            target_ip = socket.gethostbyname(self.target)
            raw_lines.append(f"Target IP: {target_ip}")
        except Exception:
            target_ip = self.target

        # Phase 1: Port scan & banner grab
        raw_lines.append("\n[Phase 1: Service Discovery]")
        open_services = []
        for port, service_name in SERVICE_PORTS:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            try:
                result = sock.connect_ex((target_ip, port))
                if result == 0:
                    banner = self._grab_banner(target_ip, port)
                    service = {
                        "port": port,
                        "name": service_name,
                        "banner": banner,
                    }
                    open_services.append(service)
                    findings.append({
                        "type": "open_service",
                        "port": port,
                        "service": service_name,
                        "banner": banner[:200] if banner else "",
                        "detail": f"{service_name} on port {port}" + (f" — {banner[:80]}" if banner else ""),
                        "severity": "info",
                    })
                    raw_lines.append(f"  Port {port}: {service_name}" +
                                     (f" — {banner[:60]}" if banner else ""))
            except Exception:
                pass
            finally:
                sock.close()

        # Phase 2: Dangerous service detection
        raw_lines.append("\n[Phase 2: Dangerous Services]")
        dangerous = {
            23: ("Telnet — unencrypted remote access!", "critical"),
            21: ("FTP — often unencrypted and vulnerable", "high"),
            161: ("SNMP — may leak system info with default community", "high"),
            139: ("NetBIOS — may expose shares and user info", "high"),
            445: ("SMB — potential for EternalBlue and other exploits", "high"),
            3389: ("RDP — brute-force and BlueKeep risk", "high"),
            5900: ("VNC — often weak/no authentication", "high"),
            111: ("RPCbind — can enumerate RPC services", "medium"),
            2049: ("NFS — may have world-readable exports", "high"),
        }
        for svc in open_services:
            if svc["port"] in dangerous:
                desc, sev = dangerous[svc["port"]]
                findings.append({
                    "type": "dangerous_service",
                    "port": svc["port"],
                    "service": svc["name"],
                    "detail": desc,
                    "severity": sev,
                })
                raw_lines.append(f"  {sev.upper()}: {desc}")

        # Phase 3: SSH configuration analysis
        raw_lines.append("\n[Phase 3: SSH Analysis]")
        ssh_services = [s for s in open_services if s["port"] in (22, 2222)]
        for svc in ssh_services:
            banner = svc.get("banner", "")
            if banner:
                # Check for old SSH versions
                if "SSH-1" in banner:
                    findings.append({
                        "type": "ssh_v1",
                        "detail": "SSH protocol version 1 supported — weak cryptography!",
                        "severity": "critical",
                    })
                    raw_lines.append("  CRITICAL: SSH v1 protocol supported!")

                # Extract version
                version_match = re.search(r"OpenSSH[_\s](\d+\.\d+)", banner)
                if version_match:
                    version = float(version_match.group(1))
                    if version < 8.0:
                        findings.append({
                            "type": "ssh_outdated",
                            "version": version_match.group(1),
                            "detail": f"OpenSSH {version_match.group(1)} — outdated, update recommended",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: OpenSSH {version_match.group(1)} outdated")
                    else:
                        raw_lines.append(f"  OK: OpenSSH {version_match.group(1)}")

        # Phase 4: SSL/TLS analysis on HTTPS port
        raw_lines.append("\n[Phase 4: SSL/TLS Analysis]")
        for port in [443, 8443]:
            if any(s["port"] == port for s in open_services):
                tls_findings = self._analyze_tls(target_ip, port)
                findings.extend(tls_findings)
                for f in tls_findings:
                    raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # Phase 5: SMTP open relay check
        raw_lines.append("\n[Phase 5: SMTP Open Relay Check]")
        smtp_ports = [p for p in [25, 587, 465] if any(s["port"] == p for s in open_services)]
        for port in smtp_ports:
            if self._check_smtp_open_relay(target_ip, port):
                findings.append({
                    "type": "smtp_open_relay",
                    "port": port,
                    "detail": f"SMTP open relay on port {port}!",
                    "severity": "critical",
                })
                raw_lines.append(f"  CRITICAL: SMTP open relay on port {port}")
            else:
                raw_lines.append(f"  OK: SMTP relay restricted on port {port}")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "47_network.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Network scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _grab_banner(self, ip: str, port: int) -> str:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((ip, port))

            # Some services need a trigger
            if port in (80, 8080, 8443):
                sock.send(b"HEAD / HTTP/1.0\r\nHost: " +
                          self.target.encode() + b"\r\n\r\n")
            elif port in (25, 587):
                pass  # SMTP sends banner on connect
            elif port == 21:
                pass  # FTP sends banner
            else:
                sock.send(b"\r\n")

            banner = sock.recv(1024).decode(errors="ignore").strip()
            sock.close()
            return banner[:300]
        except Exception:
            return ""

    def _analyze_tls(self, ip: str, port: int) -> list[dict]:
        findings = []
        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with socket.create_connection((ip, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=self.target) as ssock:
                    cert = ssock.getpeercert()
                    protocol = ssock.version()
                    cipher = ssock.cipher()

                    # Protocol version
                    if protocol and ("TLSv1.0" in protocol or "TLSv1.1" in protocol or "SSLv" in protocol):
                        findings.append({
                            "type": "weak_tls",
                            "protocol": protocol,
                            "detail": f"Weak TLS: {protocol} supported — use TLS 1.2+",
                            "severity": "high",
                        })
                    elif protocol:
                        findings.append({
                            "type": "tls_version",
                            "protocol": protocol,
                            "detail": f"TLS version: {protocol}",
                            "severity": "info",
                        })

                    # Cipher strength
                    if cipher:
                        cipher_name, tls_version, key_bits = cipher
                        if key_bits and key_bits < 128:
                            findings.append({
                                "type": "weak_cipher",
                                "cipher": cipher_name,
                                "bits": key_bits,
                                "detail": f"Weak cipher: {cipher_name} ({key_bits}-bit)",
                                "severity": "high",
                            })
                        else:
                            findings.append({
                                "type": "cipher",
                                "cipher": cipher_name,
                                "bits": key_bits,
                                "detail": f"Cipher: {cipher_name} ({key_bits}-bit)",
                                "severity": "info",
                            })
        except Exception as e:
            findings.append({
                "type": "tls_error",
                "detail": f"TLS analysis error on port {port}: {str(e)[:100]}",
                "severity": "info",
            })
        return findings

    def _check_smtp_open_relay(self, ip: str, port: int) -> bool:
        """Check for SMTP open relay (safe test)."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            sock.connect((ip, port))
            banner = sock.recv(1024).decode(errors="ignore")
            sock.send(b"EHLO test.local\r\n")
            sock.recv(1024)
            sock.send(b"MAIL FROM:<test@test.local>\r\n")
            resp = sock.recv(1024).decode(errors="ignore")
            if "250" in resp:
                sock.send(b"RCPT TO:<test@example.com>\r\n")
                resp = sock.recv(1024).decode(errors="ignore")
                sock.send(b"RSET\r\n")
                sock.recv(1024)
                sock.send(b"QUIT\r\n")
                sock.close()
                return "250" in resp
            sock.send(b"QUIT\r\n")
            sock.close()
        except Exception:
            pass
        return False
