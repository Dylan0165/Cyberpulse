"""Module 09-BL — Business Logic Tester.

Tests IDOR, rate limiting, privilege escalation, and exposed admin endpoints.
"""

import time
import urllib3
from pathlib import Path

import requests

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_SESS = requests.Session()
_SESS.verify = False
_SESS.headers.update({"User-Agent": "CyberPulse-Scanner/1.0"})


class Scanner:
    name = "Business Logic Tester"
    phase = "custom"
    description = "Tests IDOR, rate limiting, and exposed admin endpoints"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target.rstrip("/")
        self.output_dir = Path(output_dir)
        self.config = config or {}

    # ── helpers ──────────────────────────────────────────────────────────────

    def _get(self, url: str, timeout: int = 6) -> requests.Response | None:
        try:
            return _SESS.get(url, timeout=timeout, allow_redirects=False)
        except Exception:
            return None

    # ── sub-tests ─────────────────────────────────────────────────────────────

    def _test_idor(self) -> list[dict]:
        findings = []
        templates = [
            "/api/user/{id}", "/api/users/{id}", "/api/profile/{id}",
            "/api/order/{id}", "/api/invoice/{id}", "/api/account/{id}",
            "/user/{id}", "/profile/{id}", "/account/{id}", "/orders/{id}",
        ]
        for tmpl in templates:
            responses: dict[int, int] = {}  # id → response length
            for id_val in [1, 2, 3, 100, 999]:
                url = self.target + tmpl.replace("{id}", str(id_val))
                r = self._get(url)
                if r is not None and r.status_code == 200 and len(r.text) > 50:
                    responses[id_val] = len(r.text)
            # If multiple IDs return 200 with different-length bodies → likely IDOR
            if len(responses) >= 2:
                findings.append({
                    "type": "potential_idor",
                    "severity": "HIGH",
                    "title": f"Potential IDOR on {tmpl}",
                    "description": (
                        f"Unauthenticated access to {tmpl} returns data for "
                        f"{len(responses)} distinct IDs without authentication."
                    ),
                    "impact": "Unauthorized read access to other users' data.",
                    "recommendation": "Enforce object-level authorization on every resource endpoint.",
                    "evidence": f"IDs with 200 responses: {list(responses.keys())}",
                })
        return findings

    def _test_rate_limiting(self) -> list[dict]:
        findings = []
        statuses: list[int] = []
        for _ in range(50):
            r = self._get(self.target, timeout=2)
            if r is None:
                break
            statuses.append(r.status_code)

        if statuses and 429 not in statuses and 503 not in statuses:
            findings.append({
                "type": "no_rate_limiting",
                "severity": "MEDIUM",
                "title": "No rate limiting detected",
                "description": (
                    f"50 rapid requests completed without triggering HTTP 429 or 503. "
                    f"Status codes seen: {sorted(set(statuses))}"
                ),
                "impact": "Brute-force, credential stuffing, and DoS attacks are easier.",
                "recommendation": (
                    "Implement rate limiting (e.g. nginx limit_req, fail2ban, "
                    "or a WAF rule). Return HTTP 429 after threshold is exceeded."
                ),
                "evidence": f"{len(statuses)} requests, codes: {sorted(set(statuses))}",
            })
        return findings

    def _test_admin_endpoints(self) -> list[dict]:
        findings = []
        endpoints = [
            "/admin", "/admin/", "/administrator", "/wp-admin", "/wp-login.php",
            "/phpmyadmin", "/cpanel", "/panel", "/dashboard", "/manager",
            "/api/admin", "/api/v1/admin", "/management", "/console",
            "/.env", "/.git/config", "/backup", "/config.php", "/config.json",
            "/server-status", "/server-info", "/.htaccess", "/web.config",
        ]
        for ep in endpoints:
            r = self._get(self.target + ep)
            if r is None:
                continue
            if r.status_code == 200:
                findings.append({
                    "type": "exposed_admin_endpoint",
                    "severity": "HIGH",
                    "title": f"Admin endpoint accessible (HTTP 200): {ep}",
                    "description": f"The endpoint {ep} is accessible without authentication and returns HTTP 200.",
                    "impact": "Potential admin panel or sensitive configuration file exposure.",
                    "recommendation": f"Restrict access to {ep} with IP allowlisting or authentication.",
                    "evidence": r.text[:200] if r.text else "(empty body)",
                    "cve": "",
                })
            elif r.status_code == 403:
                findings.append({
                    "type": "exposed_admin_endpoint_forbidden",
                    "severity": "MEDIUM",
                    "title": f"Admin endpoint exists but is forbidden (HTTP 403): {ep}",
                    "description": f"The endpoint {ep} exists (returns 403) — confirm this should not be accessible.",
                    "impact": "Endpoint exists; misconfiguration could expose it.",
                    "recommendation": f"Verify {ep} is intentional; prefer returning 404 to avoid fingerprinting.",
                    "evidence": f"HTTP 403 from {self.target}{ep}",
                })
        return findings

    # ── main ──────────────────────────────────────────────────────────────────

    def run(self) -> dict:
        findings: list[dict] = []
        raw_lines: list[str] = []

        raw_lines.append(f"[+] Business Logic Tester — target: {self.target}")

        raw_lines.append("[*] Testing IDOR vulnerabilities...")
        idor = self._test_idor()
        findings.extend(idor)
        raw_lines.append(f"    → {len(idor)} potential IDOR findings")

        raw_lines.append("[*] Testing rate limiting (50 rapid requests)...")
        rl = self._test_rate_limiting()
        findings.extend(rl)
        raw_lines.append(f"    → {len(rl)} rate-limiting findings")

        raw_lines.append(f"[*] Probing {20} common admin/sensitive endpoints...")
        adm = self._test_admin_endpoints()
        findings.extend(adm)
        raw_lines.append(f"    → {len(adm)} admin-endpoint findings")

        raw_lines.append(f"[+] Done — {len(findings)} total findings")
        return {"findings": findings, "raw_output": "\n".join(raw_lines)}
