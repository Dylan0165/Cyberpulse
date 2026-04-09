"""Module 92 — Gobuster Directory Fuzzing.

Brute-forces directories and files using Gobuster with fallback to ffuf.
"""

import logging
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m92")

SENSITIVE_PATHS = re.compile(
    r"(admin|backup|config|secret|\.env|\.git|\.svn|\.htaccess|wp-admin|phpmyadmin|debug|test|staging)",
    re.IGNORECASE,
)


class Scanner:
    name = "Gobuster Directory Fuzzing"
    phase = "scanning"
    description = "Discovers hidden directories and files via brute-force"
    target_types = ["web", "api"]

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
            "/usr/share/wordlists/dirbuster/directory-list-2.3-small.txt",
        ]
        for wl in candidates:
            if wl and Path(wl).is_file():
                return wl
        return None

    def run(self) -> dict:
        use_ffuf = False
        if not self._tool_available("gobuster"):
            if self._tool_available("ffuf"):
                use_ffuf = True
            else:
                return {"findings": [], "raw_output": "gobuster/ffuf niet gevonden in PATH", "error": None}

        wordlist = self._find_wordlist()
        if not wordlist:
            return {"findings": [], "raw_output": "Geen wordlist gevonden", "error": None}

        output_file = self.output_dir / "m92_gobuster.txt"
        findings = []
        raw_lines = []

        try:
            if use_ffuf:
                cmd = [
                    "ffuf", "-u", f"{self.target}/FUZZ",
                    "-w", wordlist, "-o", str(output_file),
                    "-of", "csv", "-mc", "200,201,301,302,403",
                    "-t", "30", "-s",
                ]
            else:
                cmd = [
                    "gobuster", "dir",
                    "-u", self.target, "-w", wordlist,
                    "-o", str(output_file),
                    "-q", "--no-error", "-t", "30",
                ]

            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            raw_output = result.stdout + (result.stderr or "")
            raw_lines.append(raw_output[-3000:] if len(raw_output) > 3000 else raw_output)

            # Parse output (gobuster format: "/path (Status: 200) [Size: 1234]")
            if output_file.exists():
                for line in output_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue

                    path = line.split()[0] if line.split() else line
                    status_match = re.search(r"Status:\s*(\d+)", line)
                    status = int(status_match.group(1)) if status_match else 200

                    # Determine severity based on path sensitivity
                    if SENSITIVE_PATHS.search(path):
                        severity = "high" if any(
                            s in path.lower() for s in [".env", ".git", "secret", "backup"]
                        ) else "medium"
                    elif status in (200, 201):
                        severity = "info"
                    else:
                        severity = "info"

                    findings.append({
                        "type": "discovered_path",
                        "severity": severity,
                        "detail": f"{path} (HTTP {status})",
                        "path": path,
                        "status_code": status,
                    })

            raw_lines.append(f"Total paths found: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
