"""Module 91 — Nuclei Template Scanner.

Runs Nuclei vulnerability scanner with templates for critical, high, and medium findings.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m91")


class Scanner:
    name = "Nuclei Template Scanner"
    phase = "scanning"
    description = "Scans target using Nuclei templates for known vulnerabilities"
    target_types = ["web", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        if not self._tool_available("nuclei"):
            return {"findings": [], "raw_output": "nuclei niet gevonden in PATH", "error": None}

        output_file = self.output_dir / "m91_nuclei.json"
        findings = []
        raw_lines = []

        try:
            cmd = [
                "nuclei", "-u", self.target,
                "-severity", "critical,high,medium",
                "-jsonl", "-o", str(output_file),
                "-silent", "-timeout", "30",
                "-no-color",
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout, cwd=str(self.output_dir),
            )

            raw_lines.append(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
            if result.stderr:
                raw_lines.append(f"STDERR: {result.stderr[-500:]}")

            # Parse JSON lines output
            if output_file.exists():
                for line in output_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        severity = entry.get("info", {}).get("severity", "info").lower()
                        template_id = entry.get("template-id", "unknown")
                        matched = entry.get("matched-at", self.target)
                        name = entry.get("info", {}).get("name", template_id)
                        description = entry.get("info", {}).get("description", "")
                        references = entry.get("info", {}).get("reference", [])
                        if isinstance(references, str):
                            references = [references]

                        findings.append({
                            "type": f"nuclei_{template_id}",
                            "severity": severity,
                            "detail": f"{name} — {matched}",
                            "description": description,
                            "references": references[:5],
                            "template": template_id,
                        })
                    except json.JSONDecodeError:
                        continue

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout expired", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
