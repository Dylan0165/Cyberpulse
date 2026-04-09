"""Module 06 — SSL/TLS Analysis.

Checks SSL/TLS certificate validity, protocol versions, cipher suites,
and common misconfigurations.
"""

import json
import logging
import socket
import ssl
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m06")


class Scanner:
    name = "SSL/TLS Analysis"
    phase = "reconnaissance"
    description = "Analyzes SSL/TLS certificates, protocols, and cipher configuration"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"SSL/TLS analysis for {self.target}"]
        cert_info = {}

        # Get certificate details
        try:
            ctx = ssl.create_default_context()
            with socket.create_connection((self.target, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.target) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    protocol = ssock.version()

                    cert_info = {
                        "subject": dict(x[0] for x in cert.get("subject", ())),
                        "issuer": dict(x[0] for x in cert.get("issuer", ())),
                        "serial_number": cert.get("serialNumber", ""),
                        "not_before": cert.get("notBefore", ""),
                        "not_after": cert.get("notAfter", ""),
                        "san": [entry[1] for entry in cert.get("subjectAltName", ())],
                        "protocol": protocol,
                        "cipher_suite": cipher[0] if cipher else "",
                        "cipher_bits": cipher[2] if cipher and len(cipher) > 2 else 0,
                    }

                    raw_lines.append(f"  Subject: {cert_info['subject']}")
                    raw_lines.append(f"  Issuer: {cert_info['issuer']}")
                    raw_lines.append(f"  Valid: {cert_info['not_before']} - {cert_info['not_after']}")
                    raw_lines.append(f"  SANs: {', '.join(cert_info['san'][:10])}")
                    raw_lines.append(f"  Protocol: {protocol}")
                    raw_lines.append(f"  Cipher: {cipher[0] if cipher else 'N/A'} ({cipher[2] if cipher and len(cipher) > 2 else '?'} bits)")

                    findings.append({
                        "type": "ssl_certificate",
                        "subject": cert_info.get("subject", {}),
                        "issuer": cert_info.get("issuer", {}),
                        "protocol": protocol,
                        "cipher": cipher[0] if cipher else "",
                        "severity": "info",
                    })

                    # Check expiry
                    try:
                        not_after = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
                        days_left = (not_after - datetime.now()).days
                        raw_lines.append(f"  Days until expiry: {days_left}")

                        if days_left < 0:
                            findings.append({
                                "type": "ssl_expired",
                                "detail": f"Certificate expired {abs(days_left)} days ago",
                                "severity": "critical",
                            })
                        elif days_left < 30:
                            findings.append({
                                "type": "ssl_expiring_soon",
                                "detail": f"Certificate expires in {days_left} days",
                                "severity": "high",
                            })
                    except Exception:
                        pass

        except ssl.SSLCertVerificationError as e:
            findings.append({
                "type": "ssl_verification_error",
                "detail": str(e),
                "severity": "high",
            })
            raw_lines.append(f"  SSL verification error: {e}")
        except Exception as e:
            findings.append({
                "type": "ssl_connection_error",
                "detail": str(e),
                "severity": "high",
            })
            raw_lines.append(f"  SSL connection error: {e}")

        # Check for insecure protocols
        raw_lines.append("\n[Protocol Support]")
        insecure_protocols = {
            ssl.PROTOCOL_TLSv1: "TLSv1.0",
            ssl.PROTOCOL_TLSv1_1: "TLSv1.1",
        } if hasattr(ssl, "PROTOCOL_TLSv1") else {}

        for proto_const, proto_name in insecure_protocols.items():
            if self._test_protocol(proto_const):
                findings.append({
                    "type": "insecure_protocol",
                    "protocol": proto_name,
                    "detail": f"{proto_name} is supported (deprecated and insecure)",
                    "severity": "high",
                })
                raw_lines.append(f"  {proto_name}: SUPPORTED (insecure)")
            else:
                raw_lines.append(f"  {proto_name}: not supported (good)")

        # Check if HTTP redirects to HTTPS
        raw_lines.append("\n[HTTP -> HTTPS redirect]")
        try:
            import requests
            resp = requests.get(
                f"http://{self.target}",
                timeout=5,
                allow_redirects=False,
                verify=False,
            )
            if resp.status_code in (301, 302, 307, 308):
                location = resp.headers.get("location", "")
                if location.startswith("https://"):
                    raw_lines.append("  HTTP redirects to HTTPS (good)")
                else:
                    findings.append({
                        "type": "no_https_redirect",
                        "detail": f"HTTP redirects to {location} (not HTTPS)",
                        "severity": "medium",
                    })
            else:
                findings.append({
                    "type": "no_https_redirect",
                    "detail": f"HTTP returns {resp.status_code}, does not redirect to HTTPS",
                    "severity": "medium",
                })
                raw_lines.append(f"  HTTP returns {resp.status_code} (no redirect)")
        except Exception as e:
            raw_lines.append(f"  HTTP check failed: {e}")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "06_ssl.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "certificate": cert_info}, f, indent=2, default=str)

        logger.info("SSL analysis %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _test_protocol(self, protocol) -> bool:
        """Test if a specific SSL/TLS protocol version is supported."""
        try:
            ctx = ssl.SSLContext(protocol)
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((self.target, 443), timeout=5) as sock:
                with ctx.wrap_socket(sock) as ssock:
                    return True
        except Exception:
            return False
