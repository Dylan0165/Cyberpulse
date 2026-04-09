"""Nuclei — template-based vulnerability scanner."""

import json as json_mod
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


NUCLEI_SEVERITY_MAP = {
    "critical": Severity.CRITICAL,
    "high": Severity.HIGH,
    "medium": Severity.MEDIUM,
    "low": Severity.LOW,
    "info": Severity.INFO,
}


@register
class NucleiWrapper(BaseToolWrapper):
    name = "nuclei"
    display_name = "Nuclei"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["nuclei"]
    default_timeout = 600
    resource_profile = ResourceProfile(estimated_ram_mb=256, estimated_duration_s=300)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        templates = kwargs.get("templates", "")
        severity_filter = kwargs.get("severity", "critical,high,medium")
        tags = kwargs.get("tags", "")

        cmd = [
            "nuclei", "-u", url,
            "-jsonl",  # JSON lines output
            "-severity", severity_filter,
            "-silent",
        ]

        if templates:
            cmd.extend(["-t", templates])
        if tags:
            cmd.extend(["-tags", tags])

        if self._laptop_mode:
            cmd.extend(["-rl", "50", "-c", "10"])  # Rate limit & concurrency

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                data = json_mod.loads(line)
            except json_mod.JSONDecodeError:
                continue

            template_id = data.get("template-id", data.get("templateID", ""))
            name = data.get("info", {}).get("name", data.get("name", template_id))
            severity_str = data.get("info", {}).get("severity", data.get("severity", "info"))
            severity = NUCLEI_SEVERITY_MAP.get(severity_str.lower(), Severity.INFO)
            matched_at = data.get("matched-at", data.get("matched", ""))
            description = data.get("info", {}).get("description", "")
            cve_id = ""

            # Extract CVE from tags or classification
            tags = data.get("info", {}).get("tags", [])
            if isinstance(tags, str):
                tags = tags.split(",")
            classification = data.get("info", {}).get("classification", {})
            cve_ids = classification.get("cve-id", [])
            if cve_ids:
                cve_id = cve_ids[0] if isinstance(cve_ids, list) else str(cve_ids)

            refs = data.get("info", {}).get("reference", [])
            if isinstance(refs, str):
                refs = [refs]

            findings.append(ToolFinding(
                tool=self.name,
                title=f"{name}" if name else f"Nuclei: {template_id}",
                detail=f"Template: {template_id} — {matched_at}",
                severity=severity,
                description=description or f"Nuclei template '{template_id}' matched op {matched_at}.",
                cve=cve_id,
                recommendation=data.get("info", {}).get("remediation", "Onderzoek en mitigeer deze kwetsbaarheid."),
                raw_output=line[:1000],
                references=refs[:5] if refs else [],
            ))

        return findings
