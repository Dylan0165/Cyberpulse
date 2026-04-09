"""Module 14 — CORS Misconfiguration Check.

Tests Cross-Origin Resource Sharing headers for overly permissive
configurations that could be exploited.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m14")

# Origins to test
TEST_ORIGINS = [
    "https://evil.com",
    "https://attacker.com",
    "null",
    "https://{target}.evil.com",
    "https://evil-{target}",
    "https://{target}evil.com",
]


class Scanner:
    name = "CORS Misconfiguration"
    phase = "vulnerability_scan"
    description = "Tests CORS headers for overly permissive configurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"CORS misconfiguration check for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Test endpoints
        endpoints = [
            base_url,
            f"{base_url}/api",
            f"{base_url}/api/v1",
            f"{base_url}/graphql",
        ]

        for url in endpoints:
            raw_lines.append(f"\n[Testing] {url}")

            for origin_template in TEST_ORIGINS:
                origin = origin_template.replace("{target}", self.target)

                try:
                    resp = self.session.options(
                        url,
                        headers={
                            "Origin": origin,
                            "Access-Control-Request-Method": "GET",
                            "User-Agent": "Mozilla/5.0 CyberPulse/1.0",
                        },
                        timeout=8,
                    )

                    acao = resp.headers.get("Access-Control-Allow-Origin", "")
                    acac = resp.headers.get("Access-Control-Allow-Credentials", "")

                    if not acao:
                        # Try a GET request instead
                        resp = self.session.get(
                            url,
                            headers={"Origin": origin, "User-Agent": "Mozilla/5.0 CyberPulse/1.0"},
                            timeout=8,
                        )
                        acao = resp.headers.get("Access-Control-Allow-Origin", "")
                        acac = resp.headers.get("Access-Control-Allow-Credentials", "")

                    if acao:
                        raw_lines.append(f"  Origin: {origin}")
                        raw_lines.append(f"  ACAO: {acao}, ACAC: {acac}")

                        # Wildcard with credentials
                        if acao == "*" and acac.lower() == "true":
                            findings.append({
                                "type": "cors_wildcard_credentials",
                                "url": url,
                                "origin": origin,
                                "acao": acao,
                                "acac": acac,
                                "detail": "CORS allows * with credentials — critical misconfiguration",
                                "severity": "critical",
                            })
                        # Reflects arbitrary origin
                        elif acao == origin and "evil" in origin:
                            severity = "critical" if acac.lower() == "true" else "high"
                            findings.append({
                                "type": "cors_origin_reflection",
                                "url": url,
                                "origin": origin,
                                "acao": acao,
                                "acac": acac,
                                "detail": f"CORS reflects arbitrary origin '{origin}' (credentials={acac})",
                                "severity": severity,
                            })
                        # Null origin allowed
                        elif acao == "null":
                            findings.append({
                                "type": "cors_null_origin",
                                "url": url,
                                "origin": origin,
                                "acao": acao,
                                "detail": "CORS allows 'null' origin — can be exploited via sandboxed iframe",
                                "severity": "high",
                            })
                        # Wildcard without credentials (less severe)
                        elif acao == "*":
                            findings.append({
                                "type": "cors_wildcard",
                                "url": url,
                                "acao": acao,
                                "detail": "CORS allows any origin (without credentials)",
                                "severity": "medium",
                            })

                except Exception as e:
                    raw_lines.append(f"  Error with origin {origin}: {e}")

        if not findings:
            raw_lines.append("\nNo CORS misconfigurations detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "14_cors.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("CORS check %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}
