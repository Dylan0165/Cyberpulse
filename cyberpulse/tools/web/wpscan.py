"""WPScan — WordPress security scanner."""

import json as json_mod
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class WpscanWrapper(BaseToolWrapper):
    name = "wpscan"
    display_name = "WPScan"
    category = ToolCategory.WEB_EXPLOITATION
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["wpscan"]
    default_timeout = 300
    resource_profile = ResourceProfile(estimated_ram_mb=128, estimated_duration_s=180)

    def build_command(self, target: str, **kwargs) -> list[str]:
        url = target if "://" in target else f"http://{target}"
        api_token = kwargs.get("api_token", "")

        cmd = ["wpscan", "--url", url, "--format", "json", "--no-banner"]

        if api_token:
            cmd.extend(["--api-token", api_token])

        if self._laptop_mode:
            cmd.extend(["--throttle", "500"])

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []

        try:
            data = json_mod.loads(stdout)
        except json_mod.JSONDecodeError:
            if "does not seem to be running WordPress" in (stdout + stderr):
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Geen WordPress gedetecteerd",
                    detail="Het target draait geen WordPress",
                    severity=Severity.INFO,
                ))
            return findings

        # WordPress version
        wp_version = data.get("version", {})
        if wp_version:
            ver = wp_version.get("number", "")
            status = wp_version.get("status", "")
            if status == "insecure":
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Verouderde WordPress versie: {ver}",
                    detail=f"WordPress {ver} is kwetsbaar",
                    severity=Severity.HIGH,
                    description=f"WordPress versie {ver} is gemarkeerd als onveilig. "
                                "Er zijn bekende kwetsbaarheden voor deze versie.",
                    recommendation="Update WordPress naar de laatste versie.",
                ))

        # Plugins
        for name, plugin_data in data.get("plugins", {}).items():
            vulns = plugin_data.get("vulnerabilities", [])
            version = plugin_data.get("version", {}).get("number", "onbekend")
            outdated = plugin_data.get("outdated", False)

            for vuln in vulns:
                cve = ""
                refs = vuln.get("references", {})
                cve_list = refs.get("cve", [])
                if cve_list:
                    cve = f"CVE-{cve_list[0]}"

                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Kwetsbaarheid in plugin '{name}': {vuln.get('title', '')}",
                    detail=f"Plugin {name} v{version} - {vuln.get('title', '')}",
                    severity=Severity.HIGH if vuln.get("vuln_type") != "INFORMATIVE" else Severity.MEDIUM,
                    description=vuln.get("title", ""),
                    cve=cve,
                    recommendation=f"Update plugin '{name}' naar de nieuwste versie.",
                    references=[u for u in refs.get("url", [])],
                ))

            if outdated and not vulns:
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Verouderde plugin: {name} v{version}",
                    detail=f"Plugin {name} is niet up-to-date",
                    severity=Severity.LOW,
                    recommendation=f"Update plugin '{name}'.",
                ))

        # Themes
        for name, theme_data in data.get("themes", {}).items():
            for vuln in theme_data.get("vulnerabilities", []):
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Kwetsbaarheid in thema '{name}': {vuln.get('title', '')}",
                    detail=vuln.get("title", ""),
                    severity=Severity.HIGH,
                    recommendation=f"Update thema '{name}' of schakel over naar een veilig thema.",
                ))

        # Users found
        users = data.get("users", {})
        if users:
            user_list = ", ".join(users.keys())
            findings.append(ToolFinding(
                tool=self.name,
                title=f"WordPress gebruikers gevonden: {len(users)}",
                detail=f"Gebruikers: {user_list}",
                severity=Severity.MEDIUM,
                description=f"WPScan heeft {len(users)} WordPress gebruikers gevonden via enumeration.",
                recommendation="Beperk user enumeration. Gebruik een security plugin.",
            ))

        return findings
