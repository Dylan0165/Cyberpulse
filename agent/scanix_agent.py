#!/usr/bin/env python3
"""
Scanix Agent v1.0
Runs locally on the customer's server. Connects out to Scanix over HTTPS,
picks up pending scans on each heartbeat, runs them locally and streams the
output back. No inbound ports / port forwarding required.

Requires: Python 3.8+, nmap, curl. Optional: nuclei.
"""

import os
import sys
import time
import subprocess
import socket
import platform
from datetime import datetime

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is required (pip3 install requests)")
    sys.exit(1)

SCANIX_URL = os.environ.get("SCANIX_URL", "https://app.scanix.nl")
AGENT_TOKEN = os.environ.get("AGENT_TOKEN", "")
HEARTBEAT_INTERVAL = 30  # seconds


class ScanixAgent:
    def __init__(self):
        self.token = AGENT_TOKEN
        self.headers = {"X-Agent-Token": self.token}
        self.hostname = socket.gethostname()
        self.local_ip = self._get_local_ip()
        self.os = platform.system().lower()

    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "unknown"

    def heartbeat(self):
        payload = {
            "hostname": self.hostname,
            "local_ip": self.local_ip,
            "os": self.os,
            "version": "1.0.0",
        }
        try:
            resp = requests.post(
                f"{SCANIX_URL}/api/agents/heartbeat",
                json=payload, headers=self.headers, timeout=10,
            )
            data = resp.json()
            for scan in data.get("pending_scans", []):
                self.execute_scan(scan)
        except Exception as e:
            print(f"[{datetime.now()}] Heartbeat failed: {e}")

    def execute_scan(self, scan: dict):
        scan_id = scan["scan_id"]
        target = scan["target"]
        print(f"[{datetime.now()}] Starting scan {scan_id} -> {target}")

        self._run_phase(scan_id, "Phase 1: Reconnaissance", [
            f"nmap -sV -sC -O {target} -oX /tmp/scan_{scan_id}.xml",
        ])

        if self._tool_available("nuclei"):
            self._run_phase(scan_id, "Phase 2: Vulnerability Scan", [
                f"nuclei -u {target} -severity critical,high,medium",
            ])

        self._run_phase(scan_id, "Phase 6: SSL/TLS Analysis", [
            f"nmap --script ssl-enum-ciphers -p 443 {target}",
        ])

        self._send_result(scan_id, "completed", {})

    def _run_phase(self, scan_id: str, phase: str, commands: list):
        for cmd in commands:
            try:
                result = subprocess.run(
                    cmd.split(), capture_output=True, text=True, timeout=300,
                )
                self._send_result(scan_id, "output", {
                    "phase": phase,
                    "output": (result.stdout or "") + (result.stderr or ""),
                })
            except subprocess.TimeoutExpired:
                self._send_result(scan_id, "output", {
                    "phase": phase,
                    "output": f"Timeout na 5 minuten voor: {cmd}",
                })
            except FileNotFoundError:
                self._send_result(scan_id, "output", {
                    "phase": phase,
                    "output": f"Tool niet gevonden voor: {cmd}",
                })

    def _send_result(self, scan_id: str, event: str, data: dict):
        try:
            requests.post(
                f"{SCANIX_URL}/api/agents/scan-result",
                json={"scan_id": scan_id, "event": event, "data": data},
                headers=self.headers, timeout=10,
            )
        except Exception as e:
            print(f"Failed to send result: {e}")

    def _tool_available(self, tool: str) -> bool:
        try:
            return subprocess.run(["which", tool], capture_output=True).returncode == 0
        except Exception:
            return False

    def run(self):
        print(f"Scanix Agent v1.0 gestart op {self.hostname} ({self.local_ip})")
        print(f"Verbinding met: {SCANIX_URL}")
        while True:
            self.heartbeat()
            time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    if not AGENT_TOKEN:
        print("ERROR: AGENT_TOKEN niet ingesteld")
        print("Gebruik: AGENT_TOKEN=xxx python3 scanix_agent.py")
        sys.exit(1)
    ScanixAgent().run()
