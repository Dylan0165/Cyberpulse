"""Module 94 — testssl.sh TLS Audit.

Audits TLS/SSL configuration using testssl.sh.
"""

import json
import logging
import shutil
import socket
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m94")


class Scanner:
    name = "Testssl.sh TLS Audit"
    phase = "scanning"
    description = "Audits TLS/SSL configuration for weaknesses and misconfigurations"
    target_types = ["web", "api", "network"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def _has_https(self) -> bool:
        """Check if port 443 is open."""
        host = self.target.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        try:
            with socket.create_connection((host, 443), timeout=5):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def run(self) -> dict:
        if not self._tool_available("testssl.sh") and not self._tool_available("testssl"):
            return {"findings": [], "raw_output": "testssl.sh niet gevonden in PATH", "error": None}

        if not self._has_https():
            return {"findings": [], "raw_output": "Geen HTTPS (poort 443) beschikbaar", "error": None}

        tool = "testssl.sh" if self._tool_available("testssl.sh") else "testssl"
        output_file = self.output_dir / "m94_testssl.json"
        findings = []
        raw_lines = []

        # Extract hostname for testssl
        host = self.target.replace("https://", "").replace("http://", "").split("/")[0]

        try:
            cmd = [
                tool,
                f"--jsonfile={output_file}",
                "--severity", "HIGH",
                "--quiet",
                "--color", "0",
                host,
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            raw_lines.append(result.stdout[-3000:] if len(result.stdout) > 3000 else result.stdout)

            # Parse JSON output
            if output_file.exists():
                data = json.loads(output_file.read_text(encoding="utf-8"))
                entries = data if isinstance(data, list) else data.get("scanResult", [{}])[0].get("serverDefaults", [])

                for entry in (data if isinstance(data, list) else []):
                    sev = entry.get("severity", "INFO").upper()
                    finding_str = entry.get("finding", "")
                    test_id = entry.get("id", "unknown")

                    if sev == "INFO":
                        continue

                    severity_map = {
                        "CRITICAL": "critical",
                        "HIGH": "high",
                        "MEDIUM": "medium",
                        "LOW": "low",
                        "WARN": "medium",
                    }
                    severity = severity_map.get(sev, "info")

                    findings.append({
                        "type": f"tls_{test_id}",
                        "severity": severity,
                        "detail": finding_str,
                        "test_id": test_id,
                    })

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
