"""Module 98 — Gitleaks Secrets Scanner.

Scans web responses and discovered paths for leaked secrets, API keys, tokens.
"""

import json
import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m98")

# Regex patterns for secret detection when gitleaks unavailable
FALLBACK_PATTERNS = [
    (r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})', "api_key"),
    (r'(?i)(secret[_-]?key|secret)\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})', "secret_key"),
    (r'(?i)(password|passwd|pwd)\s*[:=]\s*["\']?([^\s"\']{8,})', "password"),
    (r'(?i)(token|bearer)\s*[:=]\s*["\']?([a-zA-Z0-9_\-\.]{20,})', "token"),
    (r'(?i)(aws_access_key_id)\s*[:=]\s*["\']?(AKIA[A-Z0-9]{16})', "aws_key"),
    (r'(?i)(aws_secret_access_key)\s*[:=]\s*["\']?([a-zA-Z0-9/+]{40})', "aws_secret"),
    (r'-----BEGIN\s+(RSA|EC|DSA|OPENSSH)?\s*PRIVATE\s+KEY-----', "private_key"),
]


class Scanner:
    name = "Gitleaks Secrets Scanner"
    phase = "discovery"
    description = "Scans for leaked secrets, API keys and credentials"
    target_types = ["web", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        findings = []
        raw_lines = []

        # First, try to use gitleaks on any git repos found in scraped data
        scraped_dir = self.output_dir.parent / "scraped"

        if self._tool_available("gitleaks"):
            findings_gitleaks, output = self._run_gitleaks(scraped_dir)
            findings.extend(findings_gitleaks)
            raw_lines.append(output)
        else:
            raw_lines.append("gitleaks niet gevonden — gebruik curl fallback")
            findings_curl, output = self._curl_scan()
            findings.extend(findings_curl)
            raw_lines.append(output)

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _run_gitleaks(self, scan_dir: Path) -> tuple:
        import re
        findings = []
        output_file = self.output_dir / "m98_gitleaks.json"

        # Scan source directory if available
        target_dir = scan_dir if scan_dir.exists() else self.output_dir

        try:
            cmd = [
                "gitleaks", "detect",
                "--source", str(target_dir),
                "--report-format", "json",
                "--report-path", str(output_file),
                "--no-git",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            output = result.stdout + result.stderr

            if output_file.exists():
                try:
                    leaks = json.loads(output_file.read_text(encoding="utf-8"))
                    for leak in leaks:
                        rule_id = leak.get("RuleID", "unknown")
                        file_path = leak.get("File", "unknown")
                        line = leak.get("StartLine", 0)

                        severity = "critical" if rule_id in (
                            "aws-access-key", "aws-secret-key", "private-key",
                            "github-pat", "gcp-api-key",
                        ) else "high"

                        findings.append({
                            "type": "secret_leak",
                            "severity": severity,
                            "detail": f"Gelekt secret gevonden: {rule_id} in {file_path}:{line}",
                            "rule": rule_id,
                            "file": file_path,
                            "line": line,
                        })
                except json.JSONDecodeError:
                    pass

            return findings, output[:2000]

        except subprocess.TimeoutExpired:
            return findings, "Gitleaks timeout"
        except Exception as e:
            return findings, str(e)

    def _curl_scan(self) -> tuple:
        """Check common secret-leaking paths via HTTP."""
        import re

        findings = []
        raw_lines = []
        secret_paths = [
            "/.env", "/.git/config", "/.git/HEAD",
            "/wp-config.php.bak", "/config.json", "/config.yaml",
            "/.aws/credentials", "/.docker/config.json",
            "/api/debug", "/api/config", "/.npmrc",
            "/package.json", "/composer.json",
        ]

        target = self.target.rstrip("/")

        for path in secret_paths:
            url = f"{target}{path}"
            try:
                result = subprocess.run(
                    ["curl", "-sS", "-o", "-", "-w", "\n%{http_code}",
                     "-m", "10", "--max-filesize", "1048576", url],
                    capture_output=True, text=True, timeout=15,
                )
                lines = result.stdout.rsplit("\n", 1)
                if len(lines) == 2:
                    body, status_code = lines
                else:
                    continue

                if status_code.strip() == "200" and len(body) > 10:
                    raw_lines.append(f"[200] {path} ({len(body)} bytes)")

                    # Check for secrets in response
                    for pattern, secret_type in FALLBACK_PATTERNS:
                        matches = re.findall(pattern, body)
                        if matches:
                            findings.append({
                                "type": "secret_leak",
                                "severity": "critical" if secret_type in (
                                    "aws_key", "aws_secret", "private_key"
                                ) else "high",
                                "detail": f"Mogelijk gelekt secret ({secret_type}) in {path}",
                                "path": path,
                                "secret_type": secret_type,
                            })
                            break

                    # Special: .git/config exposed
                    if path == "/.git/config" and "[core]" in body:
                        findings.append({
                            "type": "git_exposed",
                            "severity": "high",
                            "detail": f"Git repository configuratie blootgesteld op {path}",
                            "path": path,
                        })

                    # Special: .env file
                    if path == "/.env" and "=" in body:
                        findings.append({
                            "type": "env_exposed",
                            "severity": "critical",
                            "detail": f"Environment bestand blootgesteld op {path}",
                            "path": path,
                        })

            except (subprocess.TimeoutExpired, Exception):
                continue

        return findings, "\n".join(raw_lines) if raw_lines else "Geen blootgestelde paden gevonden"
