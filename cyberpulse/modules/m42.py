"""Module 42 — 2FA / MFA Bypass Testing.

Tests for weaknesses in two-factor / multi-factor authentication
implementations including bypass techniques and flawed logic.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m42")


class Scanner:
    name = "2FA/MFA Bypass Testing"
    phase = "exploitation"
    description = "Tests for weaknesses and bypass techniques in 2FA/MFA implementations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"2FA/MFA bypass testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Detect 2FA presence
        raw_lines.append("\n[Phase 1: 2FA Implementation Detection]")
        mfa_detected = False
        mfa_endpoints = [
            "/api/2fa", "/api/mfa", "/api/totp", "/api/otp",
            "/2fa", "/mfa", "/verify", "/otp",
            "/api/auth/2fa", "/api/auth/mfa", "/api/auth/verify",
            "/auth/two-factor", "/login/verify",
        ]
        for path in mfa_endpoints:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 401, 403, 405):
                    mfa_detected = True
                    findings.append({
                        "type": "mfa_endpoint",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"2FA/MFA endpoint found: {path}",
                        "severity": "info",
                    })
                    raw_lines.append(f"  INFO: 2FA endpoint {path} — HTTP {resp.status_code}")
            except Exception:
                continue

        # Also check main login page for 2FA references
        try:
            resp = self.session.get(f"{base_url}/login", timeout=10)
            mfa_keywords = ["two-factor", "2fa", "mfa", "authenticator", "totp",
                            "verification code", "security code", "otp"]
            for kw in mfa_keywords:
                if kw in resp.text.lower():
                    mfa_detected = True
                    raw_lines.append(f"  INFO: Login page references '{kw}'")
                    break
        except Exception:
            pass

        if not mfa_detected:
            findings.append({
                "type": "no_mfa",
                "detail": "No 2FA/MFA implementation detected",
                "severity": "medium",
            })
            raw_lines.append("  MEDIUM: No 2FA/MFA detected")

        # Phase 2: Direct page access bypass (skip 2FA step)
        raw_lines.append("\n[Phase 2: Direct Access Bypass]")
        protected_pages = ["/dashboard", "/profile", "/account", "/settings",
                           "/admin", "/api/user/me", "/api/profile"]
        for page in protected_pages:
            try:
                resp = self.session.get(f"{base_url}{page}", timeout=8, allow_redirects=False)
                if resp.status_code == 200:
                    # Check if we can access protected content without 2FA
                    if any(kw in resp.text.lower() for kw in ["dashboard", "profile", "settings", "account"]):
                        findings.append({
                            "type": "mfa_bypass_direct",
                            "path": page,
                            "detail": f"Protected page {page} accessible without 2FA verification",
                            "severity": "high",
                        })
                        raw_lines.append(f"  HIGH: {page} accessible without 2FA")
            except Exception:
                continue

        # Phase 3: OTP brute force potential
        raw_lines.append("\n[Phase 3: OTP Brute Force Potential]")
        otp_endpoints = ["/api/2fa/verify", "/api/otp/verify", "/verify",
                         "/api/auth/verify", "/login/verify"]
        for endpoint in otp_endpoints:
            url = base_url + endpoint
            blocked = False
            attempts = 0
            for code in ["000000", "111111", "222222", "333333", "444444",
                          "555555", "666666", "777777", "888888", "999999"]:
                try:
                    resp = self.session.post(url, json={"code": code}, timeout=5)
                    attempts += 1
                    if resp.status_code == 429:
                        blocked = True
                        raw_lines.append(f"  OK: {endpoint} rate-limited after {attempts} attempts")
                        break
                except Exception:
                    break

            if attempts >= 8 and not blocked:
                findings.append({
                    "type": "otp_no_rate_limit",
                    "endpoint": endpoint,
                    "attempts": attempts,
                    "detail": f"OTP endpoint {endpoint} not rate-limited ({attempts} attempts)",
                    "severity": "high",
                })
                raw_lines.append(f"  HIGH: OTP brute force possible at {endpoint}")

        # Phase 4: Response manipulation
        raw_lines.append("\n[Phase 4: Response Manipulation Indicators]")
        for endpoint in otp_endpoints:
            url = base_url + endpoint
            try:
                resp = self.session.post(url, json={"code": "000000"}, timeout=8)
                try:
                    data = resp.json()
                    # Check if response contains success/failure flag that could be tampered
                    if "success" in data or "verified" in data or "valid" in data:
                        findings.append({
                            "type": "mfa_response_flag",
                            "endpoint": endpoint,
                            "detail": f"2FA response contains manipulable boolean flag at {endpoint}",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: Boolean flag in 2FA response at {endpoint}")
                except Exception:
                    pass
            except Exception:
                continue

        # Phase 5: Backup code / recovery bypass
        raw_lines.append("\n[Phase 5: Backup Code & Recovery]")
        recovery_endpoints = [
            "/api/2fa/backup", "/api/mfa/recovery", "/api/auth/backup-codes",
            "/recovery", "/backup-code", "/api/2fa/disable",
        ]
        for path in recovery_endpoints:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code == 200:
                    findings.append({
                        "type": "mfa_recovery_exposed",
                        "path": path,
                        "detail": f"2FA recovery/backup endpoint accessible: {path}",
                        "severity": "high",
                    })
                    raw_lines.append(f"  HIGH: Recovery endpoint accessible {path}")
            except Exception:
                continue

            # Try to disable 2FA directly
            try:
                resp = self.session.post(url, json={"disable": True}, timeout=8)
                if resp.status_code == 200:
                    findings.append({
                        "type": "mfa_disable",
                        "path": path,
                        "detail": f"2FA may be disableable via POST to {path}",
                        "severity": "critical",
                    })
                    raw_lines.append(f"  CRITICAL: 2FA disable possible at {path}")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "42_mfa_bypass.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("2FA/MFA scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
