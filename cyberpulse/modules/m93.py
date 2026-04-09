"""Module 93 — SQLmap Injection Testing.

Automated SQL injection detection using sqlmap in safe batch mode.
"""

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m93")


class Scanner:
    name = "SQLmap Injection"
    phase = "exploitation"
    description = "Tests for SQL injection vulnerabilities using sqlmap"
    target_types = ["web", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        if not self._tool_available("sqlmap"):
            return {"findings": [], "raw_output": "sqlmap niet gevonden in PATH", "error": None}

        sqlmap_output = self.output_dir / "m93_sqlmap"
        findings = []
        raw_lines = []

        try:
            cmd = [
                "sqlmap", "-u", self.target,
                "--batch", "--random-agent",
                "--level=2", "--risk=1",
                "--forms", "--crawl=2",
                "--threads=3", "--timeout=30",
                "--no-cast",
                f"--output-dir={sqlmap_output}",
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            output = result.stdout + (result.stderr or "")
            raw_lines.append(output[-4000:] if len(output) > 4000 else output)

            # Parse sqlmap output for injection points
            injection_pattern = re.compile(
                r"Parameter:\s+['\"]?(\w+)['\"]?\s+\(([^)]+)\)",
                re.IGNORECASE,
            )
            for match in injection_pattern.finditer(output):
                param_name = match.group(1)
                injection_type = match.group(2)
                findings.append({
                    "type": "sql_injection",
                    "severity": "critical",
                    "detail": f"SQL injection gevonden op parameter '{param_name}' — type: {injection_type}",
                    "parameter": param_name,
                    "injection_type": injection_type,
                })

            # Also check for "injectable" mentions
            if "is vulnerable" in output.lower() or "injectable" in output.lower():
                # If we haven't captured specific params, add a generic finding
                if not findings:
                    findings.append({
                        "type": "sql_injection",
                        "severity": "critical",
                        "detail": "SQL injection kwetsbaarheid gedetecteerd",
                    })

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
