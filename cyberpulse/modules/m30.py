"""Module 30 — OAuth & SAML Misconfiguration Testing.

Tests OAuth 2.0 and SAML implementations for misconfigurations
including open redirects, token leakage, and improper validation.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m30")

OAUTH_PATHS = [
    "/oauth", "/oauth2", "/auth", "/authorize", "/.well-known/openid-configuration",
    "/oauth/authorize", "/oauth2/authorize", "/connect/authorize",
    "/api/oauth", "/login/oauth", "/auth/oauth",
]

SAML_PATHS = [
    "/saml", "/saml/sso", "/saml2", "/adfs/ls", "/auth/saml",
    "/sso", "/simplesaml", "/saml/metadata", "/FederationMetadata",
]


class Scanner:
    name = "OAuth & SAML Testing"
    phase = "scanning"
    description = "Tests OAuth 2.0 and SAML for misconfigurations and token leakage"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"OAuth & SAML testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: OAuth Discovery
        raw_lines.append("\n[Phase 1: OAuth Endpoint Discovery]")
        oauth_config = self._discover_oauth(base_url)
        if oauth_config:
            raw_lines.append(f"  OpenID Config found!")
            findings.append({
                "type": "oauth_config_exposed",
                "detail": "OpenID Configuration endpoint accessible",
                "severity": "info",
            })

            # Check for dangerous grant types
            grants = oauth_config.get("grant_types_supported", [])
            if "implicit" in grants:
                findings.append({
                    "type": "oauth_implicit_grant",
                    "detail": "OAuth supports deprecated implicit grant type — token leakage risk",
                    "severity": "high",
                })
                raw_lines.append("  WARNING: Implicit grant type supported!")

            if "password" in grants or "resource_owner_password_credentials" in grants:
                findings.append({
                    "type": "oauth_password_grant",
                    "detail": "OAuth supports password grant — credentials sent directly",
                    "severity": "medium",
                })

        # Phase 2: Test redirect URI validation
        raw_lines.append("\n[Phase 2: Redirect URI Validation]")
        for path in OAUTH_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=10, allow_redirects=False)
                if resp.status_code in (200, 302, 301):
                    raw_lines.append(f"  OAuth endpoint: {path}")

                    # Test open redirect
                    evil_redirects = [
                        f"https://evil.com",
                        f"https://{self.target}.evil.com",
                        f"https://evil.com/{self.target}",
                        f"//evil.com",
                        f"https://{self.target}@evil.com",
                        f"https://{self.target}%40evil.com",
                    ]

                    for evil_url in evil_redirects:
                        test_url = f"{url}?redirect_uri={evil_url}&response_type=code&client_id=test"
                        try:
                            r = self.session.get(test_url, timeout=10, allow_redirects=False)
                            location = r.headers.get("Location", "")
                            if "evil.com" in location:
                                findings.append({
                                    "type": "oauth_open_redirect",
                                    "endpoint": path,
                                    "payload": evil_url,
                                    "detail": f"OAuth redirect_uri accepts external domain: {evil_url}",
                                    "severity": "critical",
                                })
                                raw_lines.append(f"    CRITICAL: Open redirect with {evil_url}")
                                break
                        except Exception:
                            continue
            except Exception:
                continue

        # Phase 3: Token in URL check
        raw_lines.append("\n[Phase 3: Token Leakage Checks]")
        login_paths = ["/login", "/auth/login", "/signin", "/api/auth"]
        for path in login_paths:
            try:
                resp = self.session.get(base_url + path, timeout=10, allow_redirects=True)
                final_url = str(resp.url)
                if any(kw in final_url for kw in ["access_token=", "token=", "code="]):
                    findings.append({
                        "type": "oauth_token_in_url",
                        "url": final_url[:200],
                        "detail": "OAuth token/code exposed in URL — visible in logs & referrer headers",
                        "severity": "high",
                    })
                    raw_lines.append(f"  Token in URL: {final_url[:100]}")
            except Exception:
                continue

        # Phase 4: SAML Discovery
        raw_lines.append("\n[Phase 4: SAML Endpoint Discovery]")
        for path in SAML_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=10)
                if resp.status_code == 200:
                    raw_lines.append(f"  SAML endpoint: {path}")
                    findings.append({
                        "type": "saml_endpoint",
                        "path": path,
                        "detail": f"SAML endpoint found: {path}",
                        "severity": "info",
                    })

                    body = resp.text.lower()

                    # Check for SAML metadata exposure
                    if "entitydescriptor" in body or "saml" in body:
                        if "x509certificate" in body:
                            findings.append({
                                "type": "saml_metadata_exposed",
                                "path": path,
                                "detail": f"SAML metadata with certificate exposed at {path}",
                                "severity": "medium",
                            })
                            raw_lines.append(f"    Metadata + certificate exposed!")

                    # Check for SimpleSAMLphp
                    if "simplesaml" in body:
                        findings.append({
                            "type": "saml_simplesaml",
                            "path": path,
                            "detail": "SimpleSAMLphp installation detected",
                            "severity": "info",
                        })
                        # Check admin interface
                        admin_resp = self.session.get(base_url + "/simplesaml/module.php/core/frontpage_welcome.php", timeout=10)
                        if admin_resp.status_code == 200:
                            findings.append({
                                "type": "saml_admin_exposed",
                                "detail": "SimpleSAMLphp admin interface accessible",
                                "severity": "high",
                            })
                            raw_lines.append("    SimpleSAMLphp admin exposed!")
            except Exception:
                continue

        # Phase 5: Check for state parameter usage
        raw_lines.append("\n[Phase 5: CSRF Protection (state parameter)]")
        for path in OAUTH_PATHS:
            url = f"{base_url}{path}?response_type=code&client_id=test"
            try:
                resp = self.session.get(url, timeout=10, allow_redirects=False)
                location = resp.headers.get("Location", "")
                if "code=" in location and "state=" not in location:
                    findings.append({
                        "type": "oauth_no_state",
                        "endpoint": path,
                        "detail": f"OAuth flow at {path} missing state parameter — CSRF risk",
                        "severity": "high",
                    })
                    raw_lines.append(f"  Missing state parameter at {path}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "30_oauth_saml.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("OAuth/SAML scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _discover_oauth(self, base_url: str) -> dict | None:
        """Try to fetch OpenID Connect discovery document."""
        paths = [
            "/.well-known/openid-configuration",
            "/.well-known/oauth-authorization-server",
        ]
        for path in paths:
            try:
                resp = self.session.get(base_url + path, timeout=10)
                if resp.status_code == 200:
                    return resp.json()
            except Exception:
                continue
        return None

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
