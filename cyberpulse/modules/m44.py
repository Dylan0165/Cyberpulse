"""Module 44 — API Security Testing.

Comprehensive API endpoint testing: authentication, versioning,
mass assignment, excessive data exposure, and broken function-level auth.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m44")

# Common API path patterns
API_PATHS = [
    "/api", "/api/v1", "/api/v2", "/api/v3",
    "/v1", "/v2", "/rest", "/graphql",
    "/swagger.json", "/openapi.json", "/api-docs",
    "/swagger/v1/swagger.json",
    "/swagger-ui.html", "/swagger-ui/",
    "/redoc", "/docs", "/api/docs",
]

# Endpoints typically requiring auth
AUTH_ENDPOINTS = [
    "/api/users", "/api/admin", "/api/config",
    "/api/settings", "/api/internal", "/api/debug",
    "/api/v1/users", "/api/v1/admin",
]


class Scanner:
    name = "API Security Testing"
    phase = "scanning"
    description = "Tests API endpoints for authentication, authorization, and data exposure issues"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"API security testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: API documentation exposure
        raw_lines.append("\n[Phase 1: API Documentation Exposure]")
        for path in API_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=True)
                if resp.status_code == 200 and len(resp.text) > 50:
                    is_swagger = any(kw in resp.text.lower()
                                     for kw in ["swagger", "openapi", "paths", "definitions"])
                    sev = "medium" if is_swagger else "info"
                    findings.append({
                        "type": "api_docs_exposed",
                        "path": path,
                        "is_swagger": is_swagger,
                        "detail": f"API documentation exposed: {path}" +
                                  (" (Swagger/OpenAPI)" if is_swagger else ""),
                        "severity": sev,
                    })
                    raw_lines.append(f"  {'MEDIUM' if is_swagger else 'INFO'}: API docs at {path}")

                    # Parse Swagger for endpoints
                    if is_swagger:
                        try:
                            spec = resp.json()
                            paths = spec.get("paths", {})
                            raw_lines.append(f"    Swagger reveals {len(paths)} endpoints")
                        except Exception:
                            pass
            except Exception:
                continue

        # Phase 2: Broken authentication (unauthenticated access)
        raw_lines.append("\n[Phase 2: Broken Authentication]")
        for path in AUTH_ENDPOINTS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200:
                    try:
                        data = resp.json()
                        if isinstance(data, (list, dict)) and len(str(data)) > 20:
                            findings.append({
                                "type": "broken_auth",
                                "path": path,
                                "detail": f"Endpoint accessible without auth: {path}",
                                "severity": "high",
                            })
                            raw_lines.append(f"  HIGH: No auth required for {path}")
                    except Exception:
                        pass
            except Exception:
                continue

        # Phase 3: HTTP method testing (BFLA)
        raw_lines.append("\n[Phase 3: HTTP Method Testing]")
        test_endpoints = ["/api/users", "/api/users/1", "/api/config",
                          "/api/settings", "/api/admin/users"]
        dangerous_methods = ["PUT", "DELETE", "PATCH"]
        for endpoint in test_endpoints:
            url = base_url + endpoint
            for method in dangerous_methods:
                try:
                    resp = self.session.request(method, url, timeout=8, json={})
                    if resp.status_code in (200, 201, 204):
                        findings.append({
                            "type": "method_allowed",
                            "endpoint": endpoint,
                            "method": method,
                            "detail": f"{method} method allowed on {endpoint} (HTTP {resp.status_code})",
                            "severity": "high",
                        })
                        raw_lines.append(f"  HIGH: {method} allowed on {endpoint}")
                except Exception:
                    continue

        # Phase 4: Mass assignment
        raw_lines.append("\n[Phase 4: Mass Assignment]")
        mass_assign_tests = [
            ("/api/user/update", {"role": "admin", "is_admin": True}),
            ("/api/profile", {"role": "admin", "credits": 999999}),
            ("/api/register", {"username": "test", "password": "test", "role": "admin"}),
            ("/api/users", {"email": "test@test.com", "admin": True}),
        ]
        for endpoint, payload in mass_assign_tests:
            url = base_url + endpoint
            try:
                resp = self.session.post(url, json=payload, timeout=8)
                if resp.status_code in (200, 201):
                    try:
                        data = resp.json()
                        if data.get("role") in ("admin", "administrator") or data.get("is_admin"):
                            findings.append({
                                "type": "mass_assignment",
                                "endpoint": endpoint,
                                "detail": f"Mass assignment: role escalation via {endpoint}",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: Mass assignment at {endpoint}")
                    except Exception:
                        pass
            except Exception:
                continue

        # Phase 5: Excessive data exposure
        raw_lines.append("\n[Phase 5: Excessive Data Exposure]")
        data_endpoints = ["/api/users", "/api/users/1", "/api/user/me",
                          "/api/profile", "/api/accounts"]
        sensitive_fields = ["password", "password_hash", "secret", "api_key",
                            "token", "ssn", "credit_card", "card_number",
                            "private_key", "secret_key"]
        for endpoint in data_endpoints:
            url = base_url + endpoint
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200:
                    text = resp.text.lower()
                    exposed = [f for f in sensitive_fields if f in text]
                    if exposed:
                        findings.append({
                            "type": "excessive_data",
                            "endpoint": endpoint,
                            "exposed_fields": exposed,
                            "detail": f"Sensitive data in response at {endpoint}: {', '.join(exposed)}",
                            "severity": "high",
                        })
                        raw_lines.append(f"  HIGH: Sensitive fields at {endpoint}: {', '.join(exposed)}")
            except Exception:
                continue

        # Phase 6: API versioning bypass
        raw_lines.append("\n[Phase 6: API Version Bypass]")
        for endpoint in ["/api/admin", "/api/users", "/api/config"]:
            versions = ["/api/v0", "/api/v1", "/api/v2", "/api/v99",
                        "/api/latest", "/api/beta", "/api/internal"]
            for ver in versions:
                path = endpoint.replace("/api", ver)
                url = base_url + path
                try:
                    resp = self.session.get(url, timeout=5)
                    if resp.status_code == 200 and len(resp.text) > 20:
                        findings.append({
                            "type": "version_bypass",
                            "path": path,
                            "detail": f"Accessible via version bypass: {path}",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: Version bypass {path}")
                except Exception:
                    continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "44_api_security.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("API security scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
