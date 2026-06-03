"""Module 12-SW — Smart Credential Attack.

Generates a target-specific password wordlist and attempts credential testing
against discovered services (SSH, FTP, HTTP Basic) via subprocess.
"""

import json
import logging
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("cyberpulse.modules.m12_smart_wordlist")


class Scanner:
    name = "Smart Credential Attack"
    phase = "custom"
    description = "Generates smart wordlist and tests credentials against discovered services"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target.rstrip("/")
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── wordlist generation ───────────────────────────────────────────────────

    def _generate_wordlist(self) -> tuple[Path, int]:
        parsed = urlparse(self.target)
        hostname = parsed.hostname or self.target
        company = hostname.split(".")[0].lower()
        year = datetime.now().year

        words: set[str] = set()
        for base in [company, company.capitalize(), company.upper()]:
            for suffix in [
                "", "123", "1234", "12345", "123456", "!", "@", "#1",
                f"{year}", f"{year-1}", f"{year+1}", "01", "pass", "admin",
            ]:
                words.add(f"{base}{suffix}")

        words.update([
            f"Welcome{year}", "Welcome1", "Welcome123",
            "P@ssw0rd", "P@ssword1", "Password1!", "Password123",
            f"Admin{year}", "Admin123", "admin123", "Admin!",
            "letmein", "Letmein1", f"{company}pass", f"{company}2024",
            "qwerty123", "Qwerty123!", "dragon", "master",
            "Summer2024!", "Winter2024!", "Spring2025!", f"Fall{year}!",
            "Changeme1!", "changeme", "iloveyou", "abc123", "monkey",
            "test", "guest", "default", "pass", "secret",
        ])

        wordlist_path = self.output_dir / "smart_wordlist.txt"
        with open(wordlist_path, "w", encoding="utf-8") as f:
            f.write("\n".join(sorted(words)))
        return wordlist_path, len(words)

    # ── service discovery ─────────────────────────────────────────────────────

    def _get_services(self) -> list[dict]:
        services: list[dict] = []
        scan_data_file = self.output_dir / "scan_data.json"
        if not scan_data_file.exists():
            return services
        try:
            with open(scan_data_file, encoding="utf-8") as f:
                data = json.load(f)
            brute_services = {"ssh", "ftp", "telnet", "rdp", "smb", "vnc"}
            for result in data.get("results", []):
                for finding in result.get("findings", []):
                    svc = (finding.get("service") or "").lower()
                    port = finding.get("port", "")
                    if svc in brute_services and port:
                        services.append({"service": svc, "port": str(port)})
        except Exception as e:
            logger.warning("Could not read scan_data.json: %s", e)
        # Deduplicate
        seen = set()
        unique = []
        for s in services:
            k = f"{s['service']}:{s['port']}"
            if k not in seen:
                seen.add(k)
                unique.append(s)
        return unique

    # ── hydra runner ──────────────────────────────────────────────────────────

    def _run_hydra(self, service: str, port: str, wordlist: Path) -> str | None:
        if not shutil.which("hydra"):
            return None
        parsed = urlparse(self.target)
        host = parsed.hostname or self.target
        cmd = [
            "hydra",
            "-L", "/usr/share/wordlists/metasploit/unix_users.txt",
            "-P", str(wordlist),
            "-s", port,
            host, service,
            "-t", "4", "-f", "-q",
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            return "hydra timed out after 120s"
        except Exception as e:
            return f"hydra error: {e}"

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        raw_lines: list[str] = []
        scan_mode = self.config.get("scan_mode", "blackbox")

        raw_lines.append(f"[+] Smart Credential Attack — target: {self.target}")

        # Always generate wordlist
        wordlist_path, word_count = self._generate_wordlist()
        raw_lines.append(f"[*] Generated wordlist: {word_count} passwords → {wordlist_path.name}")
        findings.append({
            "type": "wordlist_generated",
            "severity": "INFO",
            "title": "Target-specific wordlist generated",
            "description": f"{word_count} target-specific passwords generated based on company name, year patterns, and common defaults.",
            "impact": "Wordlist ready for use in credential testing.",
            "recommendation": "Enforce strong password policy; use multi-factor authentication.",
            "evidence": str(wordlist_path),
        })

        # Only run hydra in graybox/whitebox mode (explicit auth testing)
        if scan_mode in ("graybox", "whitebox"):
            services = self._get_services()
            raw_lines.append(f"[*] Found {len(services)} brute-forceable services")
            for svc in services[:3]:  # limit to 3 services to avoid DoS
                raw_lines.append(f"[*] Running hydra against {svc['service']}:{svc['port']}")
                output = self._run_hydra(svc["service"], svc["port"], wordlist_path)
                if output:
                    raw_lines.append(output[:500])
                    if "login:" in output and "password:" in output:
                        for line in output.splitlines():
                            if "login:" in line and "password:" in line:
                                findings.append({
                                    "type": "weak_credentials_found",
                                    "severity": "CRITICAL",
                                    "title": f"Weak credentials on {svc['service']}:{svc['port']}",
                                    "description": f"Hydra found valid credentials: {line.strip()}",
                                    "impact": "Attacker can authenticate and gain access to the service.",
                                    "recommendation": "Change password immediately; enforce strong password policy and MFA.",
                                    "evidence": line.strip(),
                                })
        else:
            raw_lines.append("[*] Skipping live brute-force (blackbox mode — no active auth testing)")
            findings.append({
                "type": "credential_test_skipped",
                "severity": "INFO",
                "title": "Live credential testing skipped in blackbox mode",
                "description": "Use graybox or whitebox mode to enable active hydra testing.",
                "impact": "N/A",
                "recommendation": "Re-scan in graybox mode with explicit authorization.",
                "evidence": "",
            })

        raw_lines.append(f"[+] Done — {len(findings)} findings")
        return {
            "findings": findings,
            "raw_output": "\n".join(raw_lines),
            "wordlist_path": str(wordlist_path),
            "wordlist_size": word_count,
        }
