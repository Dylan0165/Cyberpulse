"""Module 95 — Feroxbuster Recursive Directory Scan.

Recursively discovers content using Feroxbuster.
"""

import json
import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m95")

SENSITIVE_PATHS = re.compile(
    r"(admin|backup|config|secret|\.env|\.git|\.svn|\.htaccess|wp-admin|debug|staging|internal)",
    re.IGNORECASE,
)


class Scanner:
    name = "Feroxbuster Recursive Scan"
    phase = "scanning"
    description = "Recursively discovers hidden content using Feroxbuster"
    target_types = ["web"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def _find_wordlist(self) -> str | None:
        candidates = [
            self.config.get("wordlist_path", ""),
            "/usr/share/wordlists/dirb/common.txt",
            "/usr/share/seclists/Discovery/Web-Content/common.txt",
        ]
        for wl in candidates:
            if wl and Path(wl).is_file():
                return wl
        return None

    def run(self) -> dict:
        if not self._tool_available("feroxbuster"):
            return {"findings": [], "raw_output": "feroxbuster niet gevonden in PATH", "error": None}

        wordlist = self._find_wordlist()
        if not wordlist:
            return {"findings": [], "raw_output": "Geen wordlist gevonden", "error": None}

        output_file = self.output_dir / "m95_feroxbuster.json"
        findings = []
        raw_lines = []

        try:
            cmd = [
                "feroxbuster",
                "-u", self.target,
                "-w", wordlist,
                "--json", "-o", str(output_file),
                "--depth", "3",
                "--silent",
                "--auto-tune",
                "--timeout", "10",
                "--threads", "30",
                "--no-state",
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            raw_lines.append(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

            if output_file.exists():
                for line in output_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        url = entry.get("url", "")
                        status = entry.get("status", 0)
                        path = entry.get("path", url)

                        if status < 200 or status >= 500:
                            continue

                        if SENSITIVE_PATHS.search(path):
                            severity = "high" if any(
                                s in path.lower() for s in [".env", ".git", "secret", "backup"]
                            ) else "medium"
                        else:
                            severity = "info"

                        findings.append({
                            "type": "discovered_path",
                            "severity": severity,
                            "detail": f"{path} (HTTP {status})",
                            "path": path,
                            "status_code": status,
                        })
                    except json.JSONDecodeError:
                        continue

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
