"""Module 48 — OWASP Top 10 Compliance Check.

Performs a structured assessment against all OWASP Top 10 (2021)
categories, aggregating checks from specialized and targeted tests.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m48")

# OWASP Top 10 (2021) categories
OWASP_2021 = {
    "A01": "Broken Access Control",
    "A02": "Cryptographic Failures",
    "A03": "Injection",
    "A04": "Insecure Design",
    "A05": "Security Misconfiguration",
    "A06": "Vulnerable and Outdated Components",
    "A07": "Identification and Authentication Failures",
    "A08": "Software and Data Integrity Failures",
    "A09": "Security Logging and Monitoring Failures",
    "A10": "Server-Side Request Forgery (SSRF)",
}


class Scanner:
    name = "OWASP Top 10 Compliance"
    phase = "scanning"
    description = "Structured assessment against all OWASP Top 10 (2021) categories"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"OWASP Top 10 (2021) compliance check for {self.target}"]
        base_url = self._get_base_url()

        # A01: Broken Access Control
        raw_lines.append("\n[A01: Broken Access Control]")
        a01 = self._check_access_control(base_url)
        findings.extend(a01)
        for f in a01:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")
        if not a01:
            raw_lines.append("  No immediate issues detected")

        # A02: Cryptographic Failures
        raw_lines.append("\n[A02: Cryptographic Failures]")
        a02 = self._check_crypto(base_url)
        findings.extend(a02)
        for f in a02:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A03: Injection
        raw_lines.append("\n[A03: Injection]")
        a03 = self._check_injection(base_url)
        findings.extend(a03)
        for f in a03:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A04: Insecure Design
        raw_lines.append("\n[A04: Insecure Design]")
        a04 = self._check_insecure_design(base_url)
        findings.extend(a04)
        for f in a04:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A05: Security Misconfiguration
        raw_lines.append("\n[A05: Security Misconfiguration]")
        a05 = self._check_misconfig(base_url)
        findings.extend(a05)
        for f in a05:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A06: Vulnerable Components
        raw_lines.append("\n[A06: Vulnerable and Outdated Components]")
        a06 = self._check_components(base_url)
        findings.extend(a06)
        for f in a06:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A07: Auth Failures
        raw_lines.append("\n[A07: Identification and Authentication Failures]")
        a07 = self._check_auth(base_url)
        findings.extend(a07)
        for f in a07:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A08: Integrity Failures
        raw_lines.append("\n[A08: Software and Data Integrity Failures]")
        a08 = self._check_integrity(base_url)
        findings.extend(a08)
        for f in a08:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A09: Logging Failures
        raw_lines.append("\n[A09: Security Logging and Monitoring Failures]")
        a09 = self._check_logging(base_url)
        findings.extend(a09)
        for f in a09:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # A10: SSRF
        raw_lines.append("\n[A10: Server-Side Request Forgery]")
        a10 = self._check_ssrf(base_url)
        findings.extend(a10)
        for f in a10:
            raw_lines.append(f"  {f['severity'].upper()}: {f['detail']}")

        # Summary
        raw_lines.append("\n[Summary]")
        for cat, name in OWASP_2021.items():
            cat_findings = [f for f in findings if f.get("owasp_category") == cat]
            status = f"{len(cat_findings)} issue(s)" if cat_findings else "PASS"
            raw_lines.append(f"  {cat}: {name} — {status}")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "48_owasp.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("OWASP Top 10 scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _check_access_control(self, base_url: str) -> list:
        results = []
        # Test IDOR
        for path in ["/api/users/1", "/api/users/2", "/admin"]:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8)
                if resp.status_code == 200:
                    results.append({
                        "type": "a01_access", "owasp_category": "A01",
                        "detail": f"Unrestricted access to {path}",
                        "severity": "high",
                    })
            except Exception:
                continue
        # CORS wildcard
        try:
            resp = self.session.get(base_url, headers={"Origin": "https://evil.com"}, timeout=8)
            acao = resp.headers.get("Access-Control-Allow-Origin", "")
            if acao == "*" or acao == "https://evil.com":
                results.append({
                    "type": "a01_cors", "owasp_category": "A01",
                    "detail": f"Permissive CORS: ACAO={acao}",
                    "severity": "medium",
                })
        except Exception:
            pass
        return results

    def _check_crypto(self, base_url: str) -> list:
        results = []
        # HTTP available (no HTTPS redirect)
        try:
            resp = requests.get(f"http://{self.target}", timeout=8,
                                allow_redirects=False, verify=False)
            if resp.status_code not in (301, 302, 308):
                results.append({
                    "type": "a02_no_https_redirect", "owasp_category": "A02",
                    "detail": "HTTP does not redirect to HTTPS",
                    "severity": "high",
                })
        except Exception:
            pass
        # HSTS header
        try:
            resp = self.session.get(base_url, timeout=8)
            if "strict-transport-security" not in {h.lower() for h in resp.headers}:
                results.append({
                    "type": "a02_no_hsts", "owasp_category": "A02",
                    "detail": "Missing HSTS header",
                    "severity": "medium",
                })
        except Exception:
            pass
        return results

    def _check_injection(self, base_url: str) -> list:
        results = []
        # Simple SQL injection test
        payloads = ["' OR '1'='1", "1; DROP TABLE test", "' UNION SELECT 1--"]
        for param in ["id", "q", "search"]:
            for payload in payloads:
                try:
                    resp = self.session.get(f"{base_url}/?{param}={payload}", timeout=8)
                    errors = ["sql syntax", "mysql", "sqlite", "postgresql",
                              "ORA-", "unclosed quotation"]
                    if any(e in resp.text.lower() for e in errors):
                        results.append({
                            "type": "a03_sqli", "owasp_category": "A03",
                            "detail": f"SQL error via '{param}' parameter",
                            "severity": "critical",
                        })
                        break
                except Exception:
                    continue
        # XSS test
        try:
            xss = "<script>alert(1)</script>"
            resp = self.session.get(f"{base_url}/?q={xss}", timeout=8)
            if xss in resp.text:
                results.append({
                    "type": "a03_xss", "owasp_category": "A03",
                    "detail": "Reflected XSS via 'q' parameter",
                    "severity": "high",
                })
        except Exception:
            pass
        return results

    def _check_insecure_design(self, base_url: str) -> list:
        results = []
        # Check for security questions, password hints
        try:
            resp = self.session.get(f"{base_url}/forgot-password", timeout=8)
            if resp.status_code == 200:
                if any(kw in resp.text.lower() for kw in
                       ["security question", "hint", "mother's maiden"]):
                    results.append({
                        "type": "a04_security_questions", "owasp_category": "A04",
                        "detail": "Insecure password recovery (security questions)",
                        "severity": "medium",
                    })
        except Exception:
            pass
        return results

    def _check_misconfig(self, base_url: str) -> list:
        results = []
        # Default error pages with stack traces
        try:
            resp = self.session.get(f"{base_url}/nonexistent_page", timeout=8)
            if resp.status_code in (404, 500):
                if any(kw in resp.text.lower() for kw in
                       ["traceback", "stack trace", "debug", "exception"]):
                    results.append({
                        "type": "a05_verbose_errors", "owasp_category": "A05",
                        "detail": "Verbose error pages expose stack traces",
                        "severity": "medium",
                    })
        except Exception:
            pass
        # Directory listing
        for path in ["/images/", "/uploads/", "/static/", "/assets/"]:
            try:
                resp = self.session.get(f"{base_url}{path}", timeout=8)
                if resp.status_code == 200 and "Index of" in resp.text:
                    results.append({
                        "type": "a05_dir_listing", "owasp_category": "A05",
                        "detail": f"Directory listing at {path}",
                        "severity": "medium",
                    })
            except Exception:
                continue
        # Security headers
        try:
            resp = self.session.get(base_url, timeout=8)
            headers_lower = {h.lower() for h in resp.headers}
            missing = []
            for h in ["x-content-type-options", "x-frame-options",
                       "content-security-policy", "referrer-policy",
                       "permissions-policy"]:
                if h not in headers_lower:
                    missing.append(h)
            if missing:
                results.append({
                    "type": "a05_missing_headers", "owasp_category": "A05",
                    "detail": f"Missing security headers: {', '.join(missing)}",
                    "severity": "medium",
                })
        except Exception:
            pass
        return results

    def _check_components(self, base_url: str) -> list:
        results = []
        try:
            resp = self.session.get(base_url, timeout=10)
            # Detect versions in HTML
            patterns = [
                (r"jQuery\s+v?(\d+\.\d+\.\d+)", "jQuery"),
                (r"bootstrap[/.](\d+\.\d+\.\d+)", "Bootstrap"),
                (r"angular[/.](\d+\.\d+\.\d+)", "Angular"),
                (r"react[/.](\d+\.\d+\.\d+)", "React"),
            ]
            for pattern, lib in patterns:
                match = re.search(pattern, resp.text, re.I)
                if match:
                    results.append({
                        "type": "a06_component", "owasp_category": "A06",
                        "detail": f"Detected {lib} version {match.group(1)} — check for known CVEs",
                        "severity": "low",
                    })
        except Exception:
            pass
        return results

    def _check_auth(self, base_url: str) -> list:
        results = []
        # Weak password policy
        try:
            resp = self.session.post(f"{base_url}/api/register",
                                     json={"username": "test", "password": "123"},
                                     timeout=8)
            if resp.status_code in (200, 201):
                results.append({
                    "type": "a07_weak_password", "owasp_category": "A07",
                    "detail": "Weak password '123' accepted during registration",
                    "severity": "high",
                })
        except Exception:
            pass
        return results

    def _check_integrity(self, base_url: str) -> list:
        results = []
        # Check for SRI on external scripts
        try:
            resp = self.session.get(base_url, timeout=10)
            ext_scripts = re.findall(
                r'<script[^>]+src=["\']https?://[^"\']+["\'][^>]*>', resp.text, re.I)
            no_sri = [s for s in ext_scripts if "integrity" not in s.lower()]
            if no_sri:
                results.append({
                    "type": "a08_no_sri", "owasp_category": "A08",
                    "detail": f"{len(no_sri)} external scripts without SRI integrity checks",
                    "severity": "medium",
                })
        except Exception:
            pass
        return results

    def _check_logging(self, base_url: str) -> list:
        results = []
        # Check if login failures produce generic vs specific errors
        try:
            resp = self.session.post(f"{base_url}/api/login",
                                     json={"username": "admin", "password": "wrong"},
                                     timeout=8)
            if "user not found" in resp.text.lower() or "invalid username" in resp.text.lower():
                results.append({
                    "type": "a09_user_enum", "owasp_category": "A09",
                    "detail": "Login error reveals whether username exists",
                    "severity": "medium",
                })
        except Exception:
            pass
        return results

    def _check_ssrf(self, base_url: str) -> list:
        results = []
        ssrf_params = ["url", "uri", "path", "src", "redirect", "next"]
        for param in ssrf_params:
            try:
                resp = self.session.get(
                    f"{base_url}/?{param}=http://169.254.169.254/latest/meta-data/",
                    timeout=8,
                )
                if resp.status_code == 200 and any(
                    kw in resp.text for kw in ["ami-id", "instance-id", "iam"]
                ):
                    results.append({
                        "type": "a10_ssrf", "owasp_category": "A10",
                        "detail": f"SSRF via '{param}' — AWS metadata accessible!",
                        "severity": "critical",
                    })
            except Exception:
                continue
        return results

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
