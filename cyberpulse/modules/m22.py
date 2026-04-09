"""Module 22 — CORS Misconfiguration Scanner.

Tests for Cross-Origin Resource Sharing misconfigurations that could
allow unauthorized cross-domain data access.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m22")

# Origins to test for CORS reflection
TEST_ORIGINS = [
    "https://evil.com",
    "https://attacker.com",
    "null",
    "https://{target}.evil.com",
    "https://evil-{target}",
    "http://{target}",           # HTTP downgrade
    "https://subdomain.{target}",
]


class Scanner:
    name = "CORS Misconfiguration"
    phase = "scanning"
    description = "Tests for dangerous Cross-Origin Resource Sharing configurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"CORS misconfiguration scan for {self.target}"]

        base_url = self._get_base_url()

        # Discover endpoints to test
        endpoints = ["/", "/api", "/api/v1", "/api/v2", "/graphql",
                     "/login", "/user", "/account", "/data"]

        for endpoint in endpoints:
            url = base_url + endpoint
            raw_lines.append(f"\n[Testing {endpoint}]")

            for origin_tmpl in TEST_ORIGINS:
                origin = origin_tmpl.replace("{target}", self.target)
                try:
                    resp = self.session.get(url, headers={"Origin": origin}, timeout=10)
                except Exception:
                    continue

                acao = resp.headers.get("Access-Control-Allow-Origin", "")
                acac = resp.headers.get("Access-Control-Allow-Credentials", "").lower()

                if not acao:
                    continue

                if acao == "*":
                    raw_lines.append(f"  Origin '{origin}' -> ACAO: * (wildcard)")
                    findings.append({
                        "type": "cors_wildcard",
                        "endpoint": endpoint,
                        "detail": f"Wildcard ACAO (*) on {endpoint}",
                        "severity": "medium" if acac != "true" else "critical",
                    })
                elif acao == origin:
                    raw_lines.append(f"  Origin '{origin}' -> REFLECTED in ACAO!")
                    severity = "high"
                    if acac == "true":
                        severity = "critical"
                        raw_lines.append(f"    + Credentials allowed! CRITICAL!")

                    findings.append({
                        "type": "cors_origin_reflected",
                        "endpoint": endpoint,
                        "origin_tested": origin,
                        "credentials": acac == "true",
                        "detail": f"Origin '{origin}' reflected in ACAO on {endpoint}" +
                                  (" with credentials" if acac == "true" else ""),
                        "severity": severity,
                    })
                elif acao == "null":
                    raw_lines.append(f"  ACAO: null accepted on {endpoint}")
                    findings.append({
                        "type": "cors_null_origin",
                        "endpoint": endpoint,
                        "detail": f"Null origin accepted on {endpoint} — possible sandboxed iframe exploit",
                        "severity": "high",
                    })

        # Check for pre-flight misconfiguration
        raw_lines.append("\n[Pre-flight (OPTIONS) checks]")
        try:
            resp = self.session.options(base_url, headers={
                "Origin": "https://evil.com",
                "Access-Control-Request-Method": "PUT",
                "Access-Control-Request-Headers": "X-Custom-Header",
            }, timeout=10)

            methods = resp.headers.get("Access-Control-Allow-Methods", "")
            headers_allowed = resp.headers.get("Access-Control-Allow-Headers", "")

            if methods:
                raw_lines.append(f"  Allowed methods: {methods}")
                dangerous = [m.strip() for m in methods.split(",")
                             if m.strip().upper() in ("PUT", "DELETE", "PATCH")]
                if dangerous:
                    findings.append({
                        "type": "cors_dangerous_methods",
                        "methods": dangerous,
                        "detail": f"Dangerous HTTP methods allowed via CORS: {', '.join(dangerous)}",
                        "severity": "medium",
                    })
            if headers_allowed:
                raw_lines.append(f"  Allowed headers: {headers_allowed}")
        except Exception as e:
            raw_lines.append(f"  Pre-flight check failed: {e}")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "22_cors.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("CORS scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
