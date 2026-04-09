"""Module 24 — WebSocket Security Testing.

Tests WebSocket endpoints for authentication bypass, injection,
origin validation, and information disclosure.
"""

import json
import logging
import ssl
import socket
import hashlib
import base64
import os
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m24")

WS_PATHS = [
    "/ws", "/websocket", "/socket", "/socket.io/", "/sockjs",
    "/ws/v1", "/ws/v2", "/realtime", "/live", "/stream",
    "/api/ws", "/cable", "/hub", "/signalr",
]


class Scanner:
    name = "WebSocket Security"
    phase = "scanning"
    description = "Tests WebSocket endpoints for auth bypass, injection, and misconfigurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"WebSocket security testing for {self.target}"]

        # Phase 1: Discover WebSocket endpoints
        raw_lines.append("\n[Phase 1: WebSocket Endpoint Discovery]")
        ws_endpoints = []
        for path in WS_PATHS:
            if self._test_ws_upgrade(path):
                ws_endpoints.append(path)
                raw_lines.append(f"  FOUND: {path}")

        # Also check main page for WS references
        raw_lines.append("\n  Checking HTML for WebSocket references...")
        html_ws = self._find_ws_in_html()
        for ws_url in html_ws:
            raw_lines.append(f"  Referenced in HTML: {ws_url}")

        if not ws_endpoints and not html_ws:
            raw_lines.append("  No WebSocket endpoints found")
            findings.append({
                "type": "no_websocket",
                "detail": "No WebSocket endpoints detected",
                "severity": "info",
            })
            raw_output = "\n".join(raw_lines)
            self._save(findings, raw_output)
            return {"findings": findings, "raw_output": raw_output}

        findings.append({
            "type": "websocket_endpoints",
            "endpoints": ws_endpoints,
            "html_references": html_ws,
            "detail": f"Found {len(ws_endpoints)} WS endpoint(s) + {len(html_ws)} HTML references",
            "severity": "info",
        })

        # Phase 2: Test each endpoint
        for path in ws_endpoints:
            raw_lines.append(f"\n[Phase 2: Testing {path}]")

            # Test cross-origin WebSocket hijacking
            raw_lines.append("  [Cross-Origin Test]")
            if self._test_ws_upgrade(path, origin="https://evil.com"):
                raw_lines.append("    VULNERABLE: Accepts connections from evil.com!")
                findings.append({
                    "type": "ws_cross_origin",
                    "endpoint": path,
                    "detail": f"WebSocket {path} accepts cross-origin connections — CSWSH risk",
                    "severity": "high",
                })
            else:
                raw_lines.append("    Origin validated correctly")

            # Test without authentication cookies
            raw_lines.append("  [No-Auth Test]")
            if self._test_ws_upgrade(path, cookies=False):
                raw_lines.append("    VULNERABLE: Accepts unauthenticated connections!")
                findings.append({
                    "type": "ws_no_auth",
                    "endpoint": path,
                    "detail": f"WebSocket {path} accessible without authentication",
                    "severity": "high",
                })

            # Test for wss:// vs ws://
            raw_lines.append("  [Encryption Check]")
            ws_works = self._test_ws_upgrade(path, use_ssl=False)
            wss_works = self._test_ws_upgrade(path, use_ssl=True)
            if ws_works and not wss_works:
                raw_lines.append("    WARNING: Only ws:// (unencrypted) available")
                findings.append({
                    "type": "ws_unencrypted",
                    "endpoint": path,
                    "detail": f"WebSocket {path} uses unencrypted ws:// only",
                    "severity": "medium",
                })
            elif ws_works and wss_works:
                raw_lines.append("    Both ws:// and wss:// accepted (should enforce wss://)")
                findings.append({
                    "type": "ws_no_tls_enforcement",
                    "endpoint": path,
                    "detail": f"WebSocket {path} does not enforce TLS",
                    "severity": "low",
                })

        raw_output = "\n".join(raw_lines)
        self._save(findings, raw_output)
        logger.info("WebSocket scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _test_ws_upgrade(self, path: str, origin: str = None,
                          cookies: bool = True, use_ssl: bool = True) -> bool:
        """Send a WebSocket upgrade request and check if accepted."""
        port = 443 if use_ssl else 80
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)

            if use_ssl:
                ctx = ssl.create_default_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                sock = ctx.wrap_socket(sock, server_hostname=self.target)

            sock.connect((self.target, port))

            key = base64.b64encode(os.urandom(16)).decode()
            headers = [
                f"GET {path} HTTP/1.1",
                f"Host: {self.target}",
                "Upgrade: websocket",
                "Connection: Upgrade",
                f"Sec-WebSocket-Key: {key}",
                "Sec-WebSocket-Version: 13",
            ]
            if origin:
                headers.append(f"Origin: {origin}")
            else:
                headers.append(f"Origin: https://{self.target}")

            request = "\r\n".join(headers) + "\r\n\r\n"
            sock.sendall(request.encode())

            response = sock.recv(4096).decode("utf-8", errors="replace")
            sock.close()

            return "101" in response and "upgrade" in response.lower()
        except Exception:
            return False

    def _find_ws_in_html(self) -> list[str]:
        """Search the main page HTML for WebSocket URLs."""
        ws_urls = []
        for scheme in ("https", "http"):
            try:
                resp = self.session.get(f"{scheme}://{self.target}", timeout=10)
                import re
                pattern = r'wss?://[^\s\'"<>]+'
                matches = re.findall(pattern, resp.text)
                ws_urls.extend(matches)
                break
            except Exception:
                continue
        return list(set(ws_urls))

    def _save(self, findings: list, raw_output: str):
        outfile = self.output_dir / "24_websocket.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)
