"""Nikto — web server vulnerability scanner."""

import json as json_mod
import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class NiktoWrapper(BaseToolWrapper):
    name = "nikto"
    display_name = "Nikto"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["nikto"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        port = kwargs.get("port", "")

        cmd = ["nikto", "-h", url, "-Format", "json", "-o", "/dev/stdout"]

        if port:
            cmd.extend(["-p", str(port)])

        if self._laptop_mode:
            cmd.extend(["-Tuning", "123"])  # Basic checks only

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        # Try JSON parsing first
        try:
            data = json_mod.loads(stdout)
            if isinstance(data, dict):
                vulns = data.get("vulnerabilities", [])
            elif isinstance(data, list):
                vulns = data
            else:
                vulns = []

            for item in vulns:
                osvdb = item.get("OSVDB", item.get("id", ""))
                msg = item.get("msg", item.get("message", ""))
                method = item.get("method", "GET")
                url = item.get("url", "")

                severity = self._classify_nikto_finding(msg, osvdb)
                findings.append(ToolFinding(
                    tool=self.name,
                    title=msg[:80] if msg else f"Nikto finding OSVDB-{osvdb}",
                    detail=f"{method} {url}: {msg}",
                    severity=severity,
                    description=msg,
                    recommendation=self._get_recommendation(msg),
                    raw_output=f"OSVDB-{osvdb}: {msg}"[:500],
                    references=[f"https://osvdb.org/{osvdb}"] if osvdb else [],
                ))
            return findings
        except (json_mod.JSONDecodeError, TypeError):
            pass

        # Fallback: parse text output
        for line in (stdout + "\n" + stderr).splitlines():
            line = line.strip()
            # Nikto text format: "+ OSVDB-xxxx: ..."  or "+ /path: Description"
            match = re.match(r"\+\s+(?:OSVDB-(\d+):\s+)?(.+)", line)
            if match:
                osvdb = match.group(1) or ""
                msg = match.group(2)
                if any(skip in msg.lower() for skip in ["target ip", "target hostname", "start time", "end time"]):
                    continue

                severity = self._classify_nikto_finding(msg, osvdb)
                findings.append(ToolFinding(
                    tool=self.name,
                    title=msg[:80],
                    detail=msg,
                    severity=severity,
                    description=msg,
                    recommendation=self._get_recommendation(msg),
                    raw_output=line[:500],
                ))

        return findings

    @staticmethod
    def _classify_nikto_finding(msg: str, osvdb: str) -> Severity:
        msg_lower = msg.lower()
        if any(w in msg_lower for w in ["remote code", "rce", "command injection", "shell"]):
            return Severity.CRITICAL
        if any(w in msg_lower for w in ["sql injection", "xss", "directory traversal", "lfi", "rfi"]):
            return Severity.HIGH
        if any(w in msg_lower for w in ["outdated", "vulnerable", "cve-", "default", "backup"]):
            return Severity.MEDIUM
        if any(w in msg_lower for w in ["information disclosure", "server header", "x-powered-by"]):
            return Severity.LOW
        return Severity.INFO

    @staticmethod
    def _get_recommendation(msg: str) -> str:
        msg_lower = msg.lower()
        if "server header" in msg_lower or "x-powered-by" in msg_lower:
            return "Verberg server version informatie in HTTP headers."
        if "directory" in msg_lower or "index" in msg_lower:
            return "Schakel directory listing uit op de webserver."
        if "backup" in msg_lower:
            return "Verwijder backup bestanden van de productieserver."
        if "default" in msg_lower:
            return "Verwijder of beveilig standaard installatie bestanden."
        return "Onderzoek deze finding en neem passende maatregelen."
