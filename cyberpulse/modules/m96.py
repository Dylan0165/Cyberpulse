"""Module 96 — Nmap NSE Vulnerability Scripts.

Runs Nmap with NSE scripts for vulnerability detection.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m96")


class Scanner:
    name = "Nmap NSE Scripts"
    phase = "scanning"
    description = "Runs Nmap vulnerability and auth NSE scripts"
    target_types = ["web", "network", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        if not self._tool_available("nmap"):
            return {"findings": [], "raw_output": "nmap niet gevonden in PATH", "error": None}

        output_file = self.output_dir / "m96_nmap_nse"
        findings = []
        raw_lines = []

        # Extract host from target
        host = self.target.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        timing = self.config.get("NMAP_TIMING", "T3")

        try:
            cmd = [
                "nmap", "-sV",
                "--script=vuln,auth,default",
                "--script-args=unsafe=0",
                "-oN", str(output_file) + ".txt",
                "-oX", str(output_file) + ".xml",
                "--open", f"-{timing}",
                host,
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            output = result.stdout
            raw_lines.append(output[-4000:] if len(output) > 4000 else output)

            # Parse for VULNERABLE markers
            vuln_pattern = re.compile(
                r"(\|_?\s*)([\w-]+):\s*(.*?VULNERABLE.*?)(?:\n\||\n\n|$)",
                re.DOTALL | re.IGNORECASE,
            )
            for match in vuln_pattern.finditer(output):
                script_name = match.group(2).strip()
                detail = match.group(3).strip()[:300]

                # Determine severity from script name
                critical_scripts = ["smb-vuln-ms17-010", "smb-vuln-ms08-067", "http-shellshock"]
                if any(cs in script_name.lower() for cs in critical_scripts):
                    severity = "critical"
                else:
                    severity = "high"

                findings.append({
                    "type": f"nse_{script_name}",
                    "severity": severity,
                    "detail": f"{script_name}: {detail}",
                    "script": script_name,
                })

            # Also look for simple "VULNERABLE" lines
            for line in output.splitlines():
                if "VULNERABLE" in line and not any(f["detail"] in line for f in findings):
                    findings.append({
                        "type": "nse_vulnerability",
                        "severity": "high",
                        "detail": line.strip()[:200],
                    })

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
