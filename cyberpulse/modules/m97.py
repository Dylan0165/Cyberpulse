"""Module 97 — WhatWeb Fingerprinting.

Identifies web technologies, frameworks, and versions.
"""

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m97")

# Known end-of-life or critically outdated software
EOL_SOFTWARE = {
    "php/5": "high", "php/4": "critical",
    "apache/2.2": "high", "apache/2.0": "critical",
    "nginx/0.": "critical", "nginx/1.0": "high",
    "jquery/1.": "medium", "jquery/2.": "medium",
    "wordpress/4.": "medium", "wordpress/3.": "high",
    "drupal/7": "medium", "drupal/6": "high",
    "openssl/0.": "critical", "openssl/1.0.1": "high",
    "python/2.": "high",
}


class Scanner:
    name = "WhatWeb Fingerprinting"
    phase = "reconnaissance"
    description = "Fingerprints web technologies, frameworks and versions"
    target_types = ["web"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        if not self._tool_available("whatweb"):
            return {"findings": [], "raw_output": "whatweb niet gevonden in PATH", "error": None}

        output_file = self.output_dir / "m97_whatweb.json"
        tech_file = self.output_dir / "m97_technologies.json"
        findings = []
        raw_lines = []
        technologies = []

        try:
            cmd = [
                "whatweb", "-a", "3",
                f"--log-json={output_file}",
                "--quiet", "--color=never",
                self.target,
            ]
            raw_lines.append(f"Running: {' '.join(cmd)}")

            result = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=self.timeout,
            )

            raw_lines.append(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)

            if output_file.exists():
                for line in output_file.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        plugins = entry.get("plugins", {})

                        for plugin_name, plugin_data in plugins.items():
                            version_list = plugin_data.get("version", [])
                            version = version_list[0] if version_list else ""
                            tech_entry = {
                                "name": plugin_name,
                                "version": version,
                            }
                            technologies.append(tech_entry)

                            # Check for outdated/EoL software
                            check_key = f"{plugin_name.lower()}/{version}" if version else ""
                            for eol_pattern, severity in EOL_SOFTWARE.items():
                                if check_key.startswith(eol_pattern):
                                    findings.append({
                                        "type": "outdated_software",
                                        "severity": severity,
                                        "detail": f"Verouderde software: {plugin_name} {version}",
                                        "software": plugin_name,
                                        "version": version,
                                    })
                                    break

                    except json.JSONDecodeError:
                        continue

            # Save technology inventory for other modules
            if technologies:
                tech_file.write_text(
                    json.dumps(technologies, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                raw_lines.append(f"Technology inventory saved: {len(technologies)} items")

            raw_lines.append(f"Total findings: {len(findings)}")
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

        except subprocess.TimeoutExpired:
            return {"findings": findings, "raw_output": "\n".join(raw_lines) + "\nTimeout", "error": "Timeout"}
        except Exception as e:
            return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": str(e)}
