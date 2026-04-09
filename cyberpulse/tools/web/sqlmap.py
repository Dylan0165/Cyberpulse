"""SQLmap — automatic SQL injection detection and exploitation."""

import json as json_mod
import re
from pathlib import Path

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class SqlmapWrapper(BaseToolWrapper):
    name = "sqlmap"
    display_name = "SQLmap"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["sqlmap"]
    default_timeout = 600
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=300)

    def build_command(self, target: str, **kwargs) -> list[str]:
        level = kwargs.get("level", "1")
        risk = kwargs.get("risk", "1")
        forms = kwargs.get("forms", False)
        crawl = kwargs.get("crawl", "0")

        url = target if "://" in target else f"http://{target}"

        cmd = [
            "sqlmap", "-u", url,
            "--batch",  # Non-interactive
            "--level", str(level),
            "--risk", str(risk),
            "--output-dir", "/tmp/sqlmap_out",
            "--flush-session",
        ]

        if forms:
            cmd.append("--forms")
        if int(crawl) > 0:
            cmd.extend(["--crawl", str(crawl)])

        if self._laptop_mode:
            cmd.extend(["--threads", "1", "--timeout", "15"])

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        # Detect injection types
        injection_types = {
            "error-based": Severity.HIGH,
            "UNION query": Severity.CRITICAL,
            "boolean-based blind": Severity.HIGH,
            "time-based blind": Severity.MEDIUM,
            "stacked queries": Severity.CRITICAL,
        }

        for inj_type, severity in injection_types.items():
            if inj_type.lower() in combined.lower():
                # Extract parameter name
                param_match = re.search(r"Parameter:\s+(\S+)", combined)
                param = param_match.group(1) if param_match else "onbekend"

                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"SQL Injection ({inj_type}) in parameter '{param}'",
                    detail=f"SQLmap vond {inj_type} SQL injection",
                    severity=severity,
                    description=f"SQLmap detecteerde een {inj_type} SQL injection kwetsbaarheid "
                                f"in parameter '{param}'. Dit stelt aanvallers in staat om "
                                "database queries te manipuleren.",
                    recommendation="Gebruik parameterized queries (prepared statements). "
                                   "Implementeer input validatie. Gebruik een WAF als extra laag.",
                    raw_output=combined[:500],
                    references=["https://owasp.org/www-community/attacks/SQL_Injection"],
                ))

        # Detect database type
        db_match = re.search(r"back-end DBMS:\s+(.+?)$", combined, re.MULTILINE)
        if db_match:
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Database geïdentificeerd: {db_match.group(1)}",
                detail=f"Backend database: {db_match.group(1)}",
                severity=Severity.INFO,
                description=f"De backend database is geïdentificeerd als {db_match.group(1)}.",
            ))

        # Detect dumped data
        if "dumped to" in combined.lower() or "entries" in combined.lower():
            entries_match = re.search(r"(\d+)\s+entries", combined)
            count = entries_match.group(1) if entries_match else "onbekend"
            findings.append(ToolFinding(
                tool=self.name,
                title=f"Database data geëxtraheerd ({count} entries)",
                detail="SQLmap kon data uit de database extraheren",
                severity=Severity.CRITICAL,
                description="SQLmap heeft succesvol data uit de database geëxtraheerd. "
                            "Dit bevestigt dat de SQL injection volledig exploiteerbaar is.",
                recommendation="Dit is een kritieke kwetsbaarheid. Fix de SQL injection onmiddellijk. "
                               "Controleer welke data is blootgesteld.",
            ))

        return findings
