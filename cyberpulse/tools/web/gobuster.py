"""Gobuster — directory and file brute-force scanner."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

SENSITIVE_PATHS = {
    "admin", "administrator", "wp-admin", "phpmyadmin", "cpanel", "webmail",
    "backup", "bak", "old", "temp", "test", "staging", "dev",
    ".git", ".svn", ".env", ".htaccess", ".htpasswd",
    "config", "conf", "setup", "install",
    "api", "swagger", "graphql",
    "upload", "uploads", "files",
}


@register
class GobusterWrapper(BaseToolWrapper):
    name = "gobuster"
    display_name = "Gobuster"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["gobuster"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        threads = kwargs.get("threads", "10")
        extensions = kwargs.get("extensions", "")
        status_codes = kwargs.get("status_codes", "200,204,301,302,307,401,403")

        cmd = [
            "gobuster", "dir",
            "-u", url,
            "-w", str(wordlist),
            "-t", str(threads),
            "-s", status_codes,
            "--no-error",
            "-q",  # Quiet, no banner
        ]

        if extensions:
            cmd.extend(["-x", extensions])

        if self._laptop_mode:
            cmd.extend(["-t", "5"])  # Lower thread count

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            # Format: "/path (Status: 200) [Size: 1234]"
            match = re.match(r"(/\S*)\s+\(Status:\s+(\d+)\)\s+\[Size:\s+(\d+)\]", line)
            if not match:
                # Alt format: "/path [Status=200] [Length=1234]"
                match = re.match(r"(/\S*)\s+\[Status=(\d+)\]", line)
            if not match:
                continue

            path = match.group(1)
            status = int(match.group(2))

            # Classify severity based on path sensitivity
            path_lower = path.lower().strip("/")
            is_sensitive = any(s in path_lower for s in SENSITIVE_PATHS)

            if is_sensitive and status in (200, 301, 302):
                severity = Severity.HIGH if any(s in path_lower for s in (".env", ".git", "config", "backup", "admin")) else Severity.MEDIUM
            elif status == 200:
                severity = Severity.LOW
            elif status == 403:
                severity = Severity.INFO
            else:
                severity = Severity.INFO

            findings.append(ToolFinding(
                tool=self.name,
                title=f"Pad gevonden: {path} (HTTP {status})",
                detail=f"Gobuster vond {path} met status {status}",
                severity=severity,
                description=f"Het pad '{path}' is bereikbaar (HTTP {status})." +
                            (" Dit is een gevoelig pad." if is_sensitive else ""),
                recommendation="Controleer of dit pad publiek toegankelijk moet zijn. "
                               "Beveilig gevoelige paden met authenticatie." if is_sensitive else "",
                raw_output=line[:500],
            ))

        return findings
