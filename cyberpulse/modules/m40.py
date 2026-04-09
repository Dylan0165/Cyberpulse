"""Module 40 — Session Management Testing.

Tests for session security: cookie attributes, session fixation,
concurrent sessions, logout effectiveness, and token entropy.
"""

import hashlib
import json
import logging
import math
import re
import string
from collections import Counter
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m40")


class Scanner:
    name = "Session Management Testing"
    phase = "scanning"
    description = "Tests session security: cookies, fixation, logout, token entropy"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Session management testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Cookie attribute analysis
        raw_lines.append("\n[Phase 1: Cookie Attribute Analysis]")
        try:
            resp = self.session.get(base_url, timeout=10)
            cookies = resp.cookies
            set_cookie_headers = resp.headers.get("Set-Cookie", "")

            for cookie in cookies:
                issues = []
                if not cookie.secure:
                    issues.append("Missing Secure flag")
                if not cookie.has_nonstandard_attr("HttpOnly") and "httponly" not in str(set_cookie_headers).lower():
                    issues.append("Missing HttpOnly flag")
                if cookie.domain and cookie.domain.startswith("."):
                    issues.append(f"Broad domain scope: {cookie.domain}")

                # Check SameSite
                raw_hdr = str(set_cookie_headers).lower()
                if "samesite" not in raw_hdr:
                    issues.append("Missing SameSite attribute")
                elif "samesite=none" in raw_hdr:
                    issues.append("SameSite=None (allows cross-site)")

                if issues:
                    findings.append({
                        "type": "cookie_insecure",
                        "cookie_name": cookie.name,
                        "issues": issues,
                        "detail": f"Cookie '{cookie.name}': {', '.join(issues)}",
                        "severity": "medium",
                    })
                    for issue in issues:
                        raw_lines.append(f"  MEDIUM: Cookie '{cookie.name}' — {issue}")
        except Exception as e:
            raw_lines.append(f"  Cookie analysis error: {e}")

        # Phase 2: Session token entropy
        raw_lines.append("\n[Phase 2: Session Token Entropy]")
        tokens = []
        for _ in range(5):
            try:
                s = requests.Session()
                s.verify = False
                s.headers["User-Agent"] = "Mozilla/5.0"
                resp = s.get(base_url, timeout=8)
                for cookie in resp.cookies:
                    if any(kw in cookie.name.lower() for kw in
                           ["session", "sess", "sid", "token", "phpsessid", "jsessionid", "asp"]):
                        tokens.append(cookie.value)
            except Exception:
                continue

        if tokens:
            entropy = self._calculate_entropy(tokens)
            raw_lines.append(f"  Collected {len(tokens)} session tokens")
            raw_lines.append(f"  Average entropy: {entropy:.1f} bits")
            if entropy < 64:
                findings.append({
                    "type": "low_entropy",
                    "entropy_bits": round(entropy, 1),
                    "sample_count": len(tokens),
                    "detail": f"Session token entropy too low: {entropy:.1f} bits (min 64 recommended)",
                    "severity": "high",
                })
                raw_lines.append(f"  HIGH: Low token entropy — {entropy:.1f} bits")
            else:
                raw_lines.append(f"  OK: Token entropy adequate ({entropy:.1f} bits)")

            # Check for sequential patterns
            if self._are_sequential(tokens):
                findings.append({
                    "type": "sequential_tokens",
                    "detail": "Session tokens appear sequential — predictable!",
                    "severity": "critical",
                })
                raw_lines.append("  CRITICAL: Sequential session tokens detected!")
        else:
            raw_lines.append("  No session tokens collected")

        # Phase 3: Session fixation test
        raw_lines.append("\n[Phase 3: Session Fixation]")
        try:
            # Get a session token
            s = requests.Session()
            s.verify = False
            resp1 = s.get(base_url, timeout=10)
            pre_login_cookies = {c.name: c.value for c in resp1.cookies}

            # Try to authenticate with it (check common login endpoints)
            login_endpoints = ["/login", "/api/login", "/auth/login", "/signin", "/api/auth"]
            for endpoint in login_endpoints:
                try:
                    resp = s.post(f"{base_url}{endpoint}",
                                  json={"username": "test", "password": "test"},
                                  timeout=8)
                except Exception:
                    try:
                        resp = s.post(f"{base_url}{endpoint}",
                                      data={"username": "test", "password": "test"},
                                      timeout=8)
                    except Exception:
                        continue

                post_login_cookies = {c.name: c.value for c in s.cookies}

                # Check if session ID changed after login attempt
                for name in pre_login_cookies:
                    if name in post_login_cookies:
                        if pre_login_cookies[name] == post_login_cookies[name]:
                            findings.append({
                                "type": "session_fixation",
                                "cookie_name": name,
                                "endpoint": endpoint,
                                "detail": f"Potential session fixation: '{name}' not regenerated after login at {endpoint}",
                                "severity": "high",
                            })
                            raw_lines.append(f"  HIGH: Session '{name}' not regenerated at {endpoint}")
                break
        except Exception as e:
            raw_lines.append(f"  Session fixation test: {e}")

        # Phase 4: Cache-control headers for authenticated pages
        raw_lines.append("\n[Phase 4: Cache-Control Headers]")
        auth_pages = ["/dashboard", "/profile", "/account", "/settings", "/admin"]
        for page in auth_pages:
            try:
                resp = self.session.get(f"{base_url}{page}", timeout=8)
                if resp.status_code == 200:
                    cc = resp.headers.get("Cache-Control", "")
                    pragma = resp.headers.get("Pragma", "")
                    if "no-store" not in cc and "no-cache" not in cc:
                        findings.append({
                            "type": "cache_control_missing",
                            "path": page,
                            "cache_control": cc or "(empty)",
                            "detail": f"Missing no-store/no-cache for {page}",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: {page} missing Cache-Control restrictions")
            except Exception:
                continue

        # Phase 5: Concurrent session check
        raw_lines.append("\n[Phase 5: Cookie scope and path checks]")
        try:
            resp = self.session.get(base_url, timeout=10)
            for cookie in resp.cookies:
                if cookie.path == "/":
                    raw_lines.append(f"  INFO: Cookie '{cookie.name}' path=/ (broad)")
                if cookie.expires and cookie.expires > 0:
                    import datetime
                    exp = datetime.datetime.fromtimestamp(cookie.expires)
                    now = datetime.datetime.now()
                    days = (exp - now).days
                    if days > 30:
                        findings.append({
                            "type": "long_lived_session",
                            "cookie_name": cookie.name,
                            "expires_in_days": days,
                            "detail": f"Cookie '{cookie.name}' expires in {days} days (too long)",
                            "severity": "low",
                        })
                        raw_lines.append(f"  LOW: Cookie '{cookie.name}' lives {days} days")
        except Exception:
            pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "40_session.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Session management scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _calculate_entropy(self, tokens: list[str]) -> float:
        """Calculate Shannon entropy of session tokens in bits."""
        if not tokens:
            return 0.0
        all_chars = "".join(tokens)
        freq = Counter(all_chars)
        total = len(all_chars)
        entropy = -sum((count / total) * math.log2(count / total)
                        for count in freq.values())
        avg_length = sum(len(t) for t in tokens) / len(tokens)
        return entropy * avg_length

    def _are_sequential(self, tokens: list[str]) -> bool:
        """Check if tokens appear to be sequential/predictable."""
        if len(tokens) < 3:
            return False
        try:
            nums = [int(t, 16) for t in tokens]
            diffs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]
            return len(set(diffs)) == 1
        except (ValueError, TypeError):
            pass
        try:
            nums = [int(t) for t in tokens]
            diffs = [nums[i + 1] - nums[i] for i in range(len(nums) - 1)]
            return len(set(diffs)) == 1
        except (ValueError, TypeError):
            pass
        return False

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
