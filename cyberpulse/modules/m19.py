"""Module 19 — API Security Testing.

Discovers and tests API endpoints for common security issues:
authentication bypass, rate limiting, information disclosure,
and improper error handling.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m19")

# Common API paths to discover
API_PATHS = [
    "api", "api/v1", "api/v2", "api/v3",
    "rest", "rest/v1",
    "graphql", "graphiql",
    "swagger.json", "swagger/v1/swagger.json",
    "openapi.json", "api-docs",
    "swagger-ui", "swagger-ui.html",
    "redoc",
    "api/health", "api/status",
    "api/users", "api/user", "api/me",
    "api/admin", "api/config",
    "api/debug", "api/test",
    "api/endpoints", "api/routes",
    ".well-known/openid-configuration",
    "oauth/token", "oauth2/token",
    "api/login", "api/register",
    "api/v1/users", "api/v1/products",
    "wp-json/wp/v2", "wp-json",
]

# HTTP methods to test
METHODS = ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"]


class Scanner:
    name = "API Security Testing"
    phase = "exploitation"
    description = "Discovers API endpoints and tests for authentication and security issues"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 CyberPulse/1.0",
            "Accept": "application/json",
        })
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"API security testing for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Discover API endpoints
        raw_lines.append("\n[API Endpoint Discovery]")
        discovered = []
        for path in API_PATHS:
            url = f"{base_url}/{path}"
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code in (200, 201, 401, 403, 405):
                    content_type = resp.headers.get("content-type", "")
                    discovered.append({
                        "url": url,
                        "status": resp.status_code,
                        "content_type": content_type,
                    })
                    raw_lines.append(f"  [{resp.status_code}] {path} ({content_type[:30]})")
            except Exception:
                pass

        raw_lines.append(f"\nDiscovered {len(discovered)} API endpoints")

        # Test each discovered endpoint
        for ep in discovered:
            url = ep["url"]

            # Test authentication bypass
            raw_lines.append(f"\n[Auth Test] {url}")
            auth_finding = self._test_auth_bypass(url)
            if auth_finding:
                findings.append(auth_finding)
                raw_lines.append(f"  [!] {auth_finding['detail']}")

            # Test HTTP method support
            methods_allowed = self._test_methods(url)
            if "DELETE" in methods_allowed or "PUT" in methods_allowed:
                findings.append({
                    "type": "api_dangerous_methods",
                    "url": url,
                    "methods": methods_allowed,
                    "detail": f"Dangerous HTTP methods allowed: {', '.join(methods_allowed)}",
                    "severity": "medium",
                })

            # Test verbose errors
            error_finding = self._test_verbose_errors(url)
            if error_finding:
                findings.append(error_finding)
                raw_lines.append(f"  [!] {error_finding['detail']}")

        # Check for exposed API documentation
        raw_lines.append("\n[API Documentation Exposure]")
        for path in ["swagger.json", "openapi.json", "api-docs", "swagger-ui", "swagger-ui.html", "redoc"]:
            url = f"{base_url}/{path}"
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200 and len(resp.text) > 100:
                    findings.append({
                        "type": "api_docs_exposed",
                        "url": url,
                        "detail": f"API documentation publicly accessible at /{path}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  [FOUND] {path}")
            except Exception:
                pass

        # Test rate limiting
        raw_lines.append("\n[Rate Limiting]")
        rate_limited = self._test_rate_limiting(base_url)
        if not rate_limited:
            findings.append({
                "type": "no_rate_limiting",
                "detail": "No rate limiting detected on API endpoints",
                "severity": "medium",
            })
            raw_lines.append("  [!] No rate limiting detected")
        else:
            raw_lines.append("  [OK] Rate limiting present")

        # Test CORS on API endpoints
        raw_lines.append("\n[API CORS]")
        for ep in discovered[:5]:
            url = ep["url"]
            try:
                resp = self.session.get(url, headers={"Origin": "https://evil.com"}, timeout=5)
                acao = resp.headers.get("Access-Control-Allow-Origin", "")
                if acao == "*" or acao == "https://evil.com":
                    findings.append({
                        "type": "api_cors_misconfiguration",
                        "url": url,
                        "acao": acao,
                        "detail": f"API endpoint reflects/allows arbitrary CORS origin",
                        "severity": "high",
                    })
                    raw_lines.append(f"  [!] {url} — ACAO: {acao}")
            except Exception:
                pass

        if not findings:
            raw_lines.append("\nNo API security issues detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "19_api.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "discovered_endpoints": discovered}, f, indent=2)

        logger.info("API security %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _test_auth_bypass(self, url: str) -> dict | None:
        """Test if an endpoint returns data without authentication."""
        try:
            resp = self.session.get(url, timeout=5)
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, (list, dict)) and len(str(data)) > 50:
                        return {
                            "type": "api_no_auth",
                            "url": url,
                            "detail": f"API endpoint returns data without authentication ({resp.status_code})",
                            "severity": "high",
                        }
                except Exception:
                    pass
        except Exception:
            pass
        return None

    def _test_methods(self, url: str) -> list[str]:
        """Test which HTTP methods are allowed on an endpoint."""
        allowed = []
        for method in METHODS:
            try:
                resp = self.session.request(method, url, timeout=3)
                if resp.status_code not in (404, 405, 501):
                    allowed.append(method)
            except Exception:
                pass
        return allowed

    def _test_verbose_errors(self, url: str) -> dict | None:
        """Test if the endpoint returns verbose error information."""
        try:
            resp = self.session.get(f"{url}/../../../etc/passwd", timeout=5)
            text = resp.text.lower()
            if any(kw in text for kw in ["traceback", "stack trace", "exception", "debug", "error at line"]):
                return {
                    "type": "api_verbose_errors",
                    "url": url,
                    "detail": "API returns verbose error messages (information leakage)",
                    "severity": "medium",
                }
        except Exception:
            pass
        return None

    def _test_rate_limiting(self, base_url: str) -> bool:
        """Test if rate limiting is enforced."""
        test_url = f"{base_url}/api"
        for _ in range(20):
            try:
                resp = self.session.get(test_url, timeout=3)
                if resp.status_code == 429:
                    return True
                if "rate limit" in resp.text.lower() or "too many" in resp.text.lower():
                    return True
            except Exception:
                pass
        return False
