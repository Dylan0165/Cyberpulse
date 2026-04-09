"""Wfuzz — web application fuzzer."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class WfuzzWrapper(BaseToolWrapper):
    name = "wfuzz"
    display_name = "Wfuzz"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["wfuzz"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        if "FUZZ" not in url:
            url = url.rstrip("/") + "/FUZZ"
        wordlist = kwargs.get("wordlist", "/usr/share/wordlists/dirb/common.txt")
        hc = kwargs.get("hide_codes", "404")
        return ["wfuzz", "-c", "-z", f"file,{wordlist}", "--hc", hc, url]

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        for line in stdout.splitlines():
            match = re.match(r"(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+\.\d+)?\s*\"(.+)\"", line.strip())
            if match:
                _id, status, lines_count, words, _time, payload = match.groups()
                status = int(status)
                if status in (200, 301, 302, 403):
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"Gevonden: /{payload} (HTTP {status})",
                        detail=f"Wfuzz vond /{payload} met status {status}",
                        severity=Severity.LOW if status == 403 else Severity.INFO,
                        raw_output=line.strip()[:300],
                    ))
        return findings
