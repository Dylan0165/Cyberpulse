"""Module 99 — Metasploit Auxiliary Scanner.

Runs ONLY auxiliary/scanner/* and auxiliary/gather/* modules.
NEVER runs exploit/* modules.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m99")

# Whitelisted Metasploit auxiliary modules — ONLY scanner and gather
ALLOWED_MODULES = [
    "auxiliary/scanner/http/http_version",
    "auxiliary/scanner/http/title",
    "auxiliary/scanner/http/robots_txt",
    "auxiliary/scanner/http/dir_scanner",
    "auxiliary/scanner/http/ssl",
    "auxiliary/scanner/http/ssl_version",
    "auxiliary/scanner/http/cert",
    "auxiliary/scanner/ssh/ssh_version",
    "auxiliary/scanner/ssh/ssh_enumusers",
    "auxiliary/scanner/ftp/ftp_version",
    "auxiliary/scanner/ftp/anonymous",
    "auxiliary/scanner/smb/smb_version",
    "auxiliary/scanner/smb/smb_enumshares",
    "auxiliary/scanner/portscan/tcp",
    "auxiliary/scanner/mysql/mysql_version",
    "auxiliary/scanner/postgres/postgres_version",
    "auxiliary/scanner/rdp/rdp_scanner",
    "auxiliary/scanner/vnc/vnc_none_auth",
    "auxiliary/scanner/telnet/telnet_version",
    "auxiliary/scanner/dns/dns_amp",
    "auxiliary/scanner/snmp/snmp_enum",
    "auxiliary/gather/http_ntlm_info_enumeration",
]


class Scanner:
    name = "Metasploit Auxiliary Scanner"
    phase = "vulnerability_scan"
    description = "Runs Metasploit auxiliary scanners (NEVER exploits)"
    target_types = ["web", "network", "api"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 600)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def _extract_host(self, target: str) -> str:
        """Extract host from URL."""
        target = target.strip()
        if "://" in target:
            target = target.split("://", 1)[1]
        target = target.split("/")[0].split(":")[0]
        return target

    def _is_allowed_module(self, module: str) -> bool:
        """SAFETY: Only allow auxiliary/scanner/* and auxiliary/gather/* modules."""
        return (
            module.startswith("auxiliary/scanner/") or
            module.startswith("auxiliary/gather/")
        ) and not module.startswith("exploit/")

    def run(self) -> dict:
        if not self._tool_available("msfconsole"):
            return {
                "findings": [],
                "raw_output": "msfconsole niet gevonden in PATH",
                "error": None,
            }

        findings = []
        raw_lines = []
        host = self._extract_host(self.target)

        # Determine which modules to run based on target
        modules_to_run = self._select_modules(host)
        raw_lines.append(f"Selected {len(modules_to_run)} auxiliary modules for {host}")

        for module_name in modules_to_run:
            # SAFETY CHECK: Double-verify module is allowed
            if not self._is_allowed_module(module_name):
                raw_lines.append(f"BLOCKED: {module_name} — niet toegestaan")
                continue

            f, o = self._run_module(module_name, host)
            findings.extend(f)
            raw_lines.append(o)

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _select_modules(self, host: str) -> list:
        """Select relevant auxiliary modules based on target."""
        # Always run common scanners
        selected = [
            "auxiliary/scanner/portscan/tcp",
            "auxiliary/scanner/http/http_version",
            "auxiliary/scanner/http/robots_txt",
            "auxiliary/scanner/http/ssl",
        ]

        # Add service-specific modules based on what we already know
        tech_file = self.output_dir / "m97_technologies.json"
        if tech_file.exists():
            try:
                techs = json.loads(tech_file.read_text(encoding="utf-8"))
                tech_names = {t.get("name", "").lower() for t in techs}

                if any("ssh" in t for t in tech_names):
                    selected.append("auxiliary/scanner/ssh/ssh_version")
                if any("ftp" in t for t in tech_names):
                    selected.extend([
                        "auxiliary/scanner/ftp/ftp_version",
                        "auxiliary/scanner/ftp/anonymous",
                    ])
                if any("smb" in t or "samba" in t for t in tech_names):
                    selected.extend([
                        "auxiliary/scanner/smb/smb_version",
                        "auxiliary/scanner/smb/smb_enumshares",
                    ])
            except Exception:
                pass

        # Deduplicate and filter
        return [m for m in dict.fromkeys(selected) if m in ALLOWED_MODULES]

    def _run_module(self, module_name: str, host: str) -> tuple:
        """Run a single Metasploit auxiliary module."""
        findings = []
        short_name = module_name.rsplit("/", 1)[-1]

        # Build resource script
        rc_content = f"""use {module_name}
set RHOSTS {host}
set THREADS 4
run
exit
"""
        rc_file = self.output_dir / f"m99_{short_name}.rc"
        rc_file.write_text(rc_content, encoding="utf-8")

        try:
            result = subprocess.run(
                ["msfconsole", "-q", "-r", str(rc_file)],
                capture_output=True, text=True,
                timeout=120,  # Per-module timeout
            )
            output = result.stdout

            # Parse output for findings
            lines = output.splitlines()
            for line in lines:
                line_clean = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()

                if not line_clean:
                    continue

                # [+] lines indicate positive results
                if line_clean.startswith("[+]"):
                    severity = "medium"
                    detail = line_clean[3:].strip()

                    # Specific severity escalation
                    if any(w in detail.lower() for w in ("anonymous", "no auth", "none auth")):
                        severity = "high"
                    if any(w in detail.lower() for w in ("vulnerable", "vuln")):
                        severity = "high"

                    findings.append({
                        "type": f"msf_{short_name}",
                        "severity": severity,
                        "detail": f"[MSF {short_name}] {detail}",
                        "module": module_name,
                    })

            return findings, f"[{short_name}] {len(findings)} findings"

        except subprocess.TimeoutExpired:
            return findings, f"[{short_name}] Timeout"
        except Exception as e:
            return findings, f"[{short_name}] Error: {e}"
