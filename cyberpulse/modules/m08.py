"""Module 08 — HTTP Header Analysis.

Deep analysis of HTTP response headers for security misconfigurations,
information leakage, and best practices compliance.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m08")

# Expected security headers and their ideal values
SECURITY_HEADERS = {
    "strict-transport-security": {
        "name": "HSTS",
        "severity": "high",
        "ideal": "max-age >= 31536000, includeSubDomains",
    },
    "content-security-policy": {
        "name": "CSP",
        "severity": "high",
        "ideal": "Restrict sources for scripts, styles, images",
    },
    "x-content-type-options": {
        "name": "X-Content-Type-Options",
        "severity": "medium",
        "ideal": "nosniff",
    },
    "x-frame-options": {
        "name": "X-Frame-Options",
        "severity": "medium",
        "ideal": "DENY or SAMEORIGIN",
    },
    "referrer-policy": {
        "name": "Referrer-Policy",
        "severity": "low",
        "ideal": "strict-origin-when-cross-origin or no-referrer",
    },
    "permissions-policy": {
        "name": "Permissions-Policy",
        "severity": "low",
        "ideal": "Restrict camera, microphone, geolocation, etc.",
    },
    "x-xss-protection": {
        "name": "X-XSS-Protection",
        "severity": "low",
        "ideal": "0 (rely on CSP instead) or 1; mode=block",
    },
    "cross-origin-opener-policy": {
        "name": "COOP",
        "severity": "low",
        "ideal": "same-origin",
    },
    "cross-origin-resource-policy": {
        "name": "CORP",
        "severity": "low",
        "ideal": "same-origin",
    },
}

# Headers that leak information
LEAK_HEADERS = ["server", "x-powered-by", "x-aspnet-version", "x-aspnetmvc-version", "x-generator"]


class Scanner:
    name = "HTTP Header Analysis"
    phase = "vulnerability_scan"
    description = "Analyzes HTTP headers for security misconfigurations and info leakage"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"HTTP header analysis for {self.target}"]
        all_headers = {}

        for scheme in ("https", "http"):
            url = f"{scheme}://{self.target}"
            try:
                resp = requests.get(
                    url,
                    timeout=10,
                    allow_redirects=True,
                    verify=False,
                    headers={"User-Agent": "Mozilla/5.0 CyberPulse/1.0"},
                )
                headers = {k.lower(): v for k, v in resp.headers.items()}
                all_headers = headers
                raw_lines.append(f"\n[{url}] Status: {resp.status_code}")

                # List all headers
                raw_lines.append("\nAll headers:")
                for k, v in sorted(headers.items()):
                    raw_lines.append(f"  {k}: {v[:120]}")

                # Check security headers
                raw_lines.append("\n[Security Headers Check]")
                for header_key, info in SECURITY_HEADERS.items():
                    if header_key in headers:
                        raw_lines.append(f"  [OK] {info['name']}: {headers[header_key][:80]}")
                        self._validate_header(header_key, headers[header_key], info, findings)
                    else:
                        raw_lines.append(f"  [MISSING] {info['name']}")
                        findings.append({
                            "type": "missing_security_header",
                            "header": info["name"],
                            "ideal": info["ideal"],
                            "severity": info["severity"],
                        })

                # Check information leakage
                raw_lines.append("\n[Information Leakage]")
                for header in LEAK_HEADERS:
                    if header in headers:
                        raw_lines.append(f"  [LEAK] {header}: {headers[header]}")
                        findings.append({
                            "type": "information_leakage",
                            "header": header,
                            "value": headers[header],
                            "detail": f"Header '{header}' reveals server technology",
                            "severity": "low",
                        })

                # Check cookie security
                raw_lines.append("\n[Cookie Security]")
                for cookie in resp.cookies:
                    issues = []
                    if not cookie.secure:
                        issues.append("missing Secure flag")
                    if "httponly" not in str(cookie._rest).lower():
                        issues.append("missing HttpOnly flag")
                    if "samesite" not in str(cookie._rest).lower():
                        issues.append("missing SameSite flag")

                    if issues:
                        raw_lines.append(f"  [WARN] Cookie '{cookie.name}': {', '.join(issues)}")
                        findings.append({
                            "type": "insecure_cookie",
                            "cookie": cookie.name,
                            "issues": issues,
                            "severity": "medium",
                        })
                    else:
                        raw_lines.append(f"  [OK] Cookie '{cookie.name}': properly secured")

                break  # Only process first successful request
            except requests.RequestException as e:
                raw_lines.append(f"\n[{url}] Error: {e}")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "08_headers.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "headers": all_headers}, f, indent=2)

        logger.info("Header analysis %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _validate_header(key: str, value: str, info: dict, findings: list):
        """Validate specific header values for known misconfigurations."""
        val_lower = value.lower()

        if key == "strict-transport-security":
            if "max-age" in val_lower:
                import re
                m = re.search(r"max-age=(\d+)", val_lower)
                if m and int(m.group(1)) < 31536000:
                    findings.append({
                        "type": "weak_hsts",
                        "detail": f"HSTS max-age is {m.group(1)} (should be >= 31536000)",
                        "severity": "medium",
                    })
            if "includesubdomains" not in val_lower:
                findings.append({
                    "type": "hsts_no_subdomains",
                    "detail": "HSTS does not include includeSubDomains directive",
                    "severity": "low",
                })

        elif key == "content-security-policy":
            if "unsafe-inline" in val_lower:
                findings.append({
                    "type": "weak_csp",
                    "detail": "CSP allows 'unsafe-inline' which weakens XSS protection",
                    "severity": "medium",
                })
            if "unsafe-eval" in val_lower:
                findings.append({
                    "type": "weak_csp",
                    "detail": "CSP allows 'unsafe-eval' which enables code injection",
                    "severity": "medium",
                })
            if "*" in value:
                findings.append({
                    "type": "weak_csp",
                    "detail": "CSP contains wildcard (*) source",
                    "severity": "high",
                })

        elif key == "x-frame-options":
            if val_lower not in ("deny", "sameorigin"):
                findings.append({
                    "type": "weak_xfo",
                    "detail": f"Unexpected X-Frame-Options value: {value}",
                    "severity": "medium",
                })
