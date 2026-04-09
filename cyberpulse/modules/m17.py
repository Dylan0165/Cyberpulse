"""Module 17 — Authentication Testing.

Tests login forms for common authentication weaknesses: default credentials,
brute-force protection, lockout policies, and password policy issues.
"""

import json
import logging
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m17")

# Common login paths
LOGIN_PATHS = [
    "login", "signin", "sign-in", "auth", "authenticate",
    "admin", "admin/login", "administrator", "wp-login.php",
    "user/login", "accounts/login", "panel", "portal",
    "dashboard/login", "cpanel", "webmail",
]

# Default credentials to test (educational purposes only - never use in prod)
DEFAULT_CREDS = [
    ("admin", "admin"),
    ("admin", "password"),
    ("admin", "123456"),
    ("admin", "admin123"),
    ("root", "root"),
    ("root", "toor"),
    ("test", "test"),
    ("user", "user"),
    ("guest", "guest"),
    ("demo", "demo"),
]


class Scanner:
    name = "Authentication Testing"
    phase = "vulnerability_scan"
    description = "Tests for authentication weaknesses and default credentials"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Authentication testing for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Find login pages
        login_pages = self._find_login_pages(base_url)
        raw_lines.append(f"Found {len(login_pages)} login pages")

        for login_info in login_pages:
            login_url = login_info["url"]
            raw_lines.append(f"\n[Testing] {login_url}")

            # Extract form details
            form_info = self._analyze_login_form(login_url)
            if not form_info:
                raw_lines.append("  No login form detected")
                continue

            raw_lines.append(f"  Form action: {form_info['action']}")
            raw_lines.append(f"  Username field: {form_info['username_field']}")
            raw_lines.append(f"  Password field: {form_info['password_field']}")

            # Check for HTTPS
            if login_url.startswith("http://"):
                findings.append({
                    "type": "login_no_https",
                    "url": login_url,
                    "detail": "Login form served over HTTP (credentials sent in cleartext)",
                    "severity": "critical",
                })
                raw_lines.append("  [!] Login over HTTP (no encryption)")

            # Check autocomplete
            if form_info.get("autocomplete_on"):
                findings.append({
                    "type": "login_autocomplete",
                    "url": login_url,
                    "detail": "Password field allows autocomplete",
                    "severity": "low",
                })

            # Test default credentials
            raw_lines.append("\n  [Default Credentials]")
            for username, password in DEFAULT_CREDS:
                result = self._test_login(form_info, username, password)
                if result == "success":
                    raw_lines.append(f"  [!] Default creds work: {username}:{password}")
                    findings.append({
                        "type": "default_credentials",
                        "url": login_url,
                        "username": username,
                        "detail": f"Default credentials {username}:{password} accepted",
                        "severity": "critical",
                    })
                    break  # Don't test more if one works
                elif result == "locked":
                    raw_lines.append("  Account lockout detected (good)")
                    findings.append({
                        "type": "account_lockout_present",
                        "url": login_url,
                        "detail": "Account lockout policy detected",
                        "severity": "info",
                    })
                    break
                time.sleep(0.5)  # Be respectful

            # Test brute-force protection
            raw_lines.append("\n  [Brute-Force Protection]")
            has_lockout = self._test_lockout(form_info)
            if not has_lockout:
                findings.append({
                    "type": "no_lockout",
                    "url": login_url,
                    "detail": "No account lockout after multiple failed attempts",
                    "severity": "high",
                })
                raw_lines.append("  [!] No lockout policy detected")
            else:
                raw_lines.append("  [OK] Lockout/rate-limiting detected")

            # Check for username enumeration
            raw_lines.append("\n  [Username Enumeration]")
            enum_result = self._test_username_enum(form_info)
            if enum_result:
                findings.append({
                    "type": "username_enumeration",
                    "url": login_url,
                    "detail": enum_result,
                    "severity": "medium",
                })
                raw_lines.append(f"  [!] {enum_result}")

        if not findings:
            raw_lines.append("\nNo authentication weaknesses detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "17_auth.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Auth testing %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _find_login_pages(self, base_url: str) -> list[dict]:
        """Find login pages by checking common paths."""
        login_pages = []
        for path in LOGIN_PATHS:
            url = f"{base_url}/{path}"
            try:
                resp = self.session.get(url, timeout=5, allow_redirects=True)
                if resp.status_code == 200:
                    lower = resp.text.lower()
                    if any(kw in lower for kw in ["password", "login", "sign in", "inloggen", "wachtwoord"]):
                        login_pages.append({"url": url, "path": path})
            except Exception:
                pass
        return login_pages[:5]

    def _analyze_login_form(self, url: str) -> dict | None:
        """Parse a login page to extract form details."""
        try:
            resp = self.session.get(url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            for form in soup.find_all("form"):
                password_field = form.find("input", {"type": "password"})
                if not password_field:
                    continue

                username_field = None
                for inp in form.find_all("input"):
                    t = (inp.get("type") or "text").lower()
                    if t in ("text", "email", "tel") and inp.get("name"):
                        username_field = inp
                        break

                if not username_field:
                    continue

                action = form.get("action", "")
                form_url = urljoin(url, action) if action else url
                method = form.get("method", "POST").upper()

                # Get hidden fields
                hidden = {}
                for h in form.find_all("input", {"type": "hidden"}):
                    name = h.get("name")
                    if name:
                        hidden[name] = h.get("value", "")

                return {
                    "action": form_url,
                    "method": method,
                    "username_field": username_field.get("name", ""),
                    "password_field": password_field.get("name", ""),
                    "hidden_fields": hidden,
                    "autocomplete_on": password_field.get("autocomplete") != "off",
                }
        except Exception:
            pass
        return None

    def _test_login(self, form_info: dict, username: str, password: str) -> str:
        """Test a single login attempt. Returns 'success', 'failed', or 'locked'."""
        data = dict(form_info["hidden_fields"])
        data[form_info["username_field"]] = username
        data[form_info["password_field"]] = password

        try:
            if form_info["method"] == "POST":
                resp = self.session.post(form_info["action"], data=data, timeout=10, allow_redirects=True)
            else:
                resp = self.session.get(form_info["action"], params=data, timeout=10, allow_redirects=True)

            lower = resp.text.lower()
            if any(kw in lower for kw in ["locked", "geblokkeerd", "too many", "te veel"]):
                return "locked"
            if any(kw in lower for kw in ["dashboard", "welcome", "welkom", "logout", "uitloggen", "profile", "profiel"]):
                return "success"
            if resp.status_code in (301, 302) and "login" not in (resp.headers.get("Location", "")).lower():
                return "success"
        except Exception:
            pass
        return "failed"

    def _test_lockout(self, form_info: dict) -> bool:
        """Test if multiple failed logins trigger lockout/rate-limiting."""
        for i in range(6):
            result = self._test_login(form_info, f"lockout_test_{i}", "wrong_password_123")
            if result == "locked":
                return True
            time.sleep(0.3)
        return False

    def _test_username_enum(self, form_info: dict) -> str | None:
        """Check if error messages differ between valid/invalid usernames."""
        try:
            resp1_text = self._get_error_message(form_info, "definitely_not_a_real_user_xyz", "wrongpass")
            resp2_text = self._get_error_message(form_info, "admin", "wrongpass123")

            if resp1_text and resp2_text and resp1_text != resp2_text:
                return "Different error messages for valid/invalid usernames (enables enumeration)"
        except Exception:
            pass
        return None

    def _get_error_message(self, form_info: dict, username: str, password: str) -> str:
        """Get the error message from a failed login attempt."""
        data = dict(form_info["hidden_fields"])
        data[form_info["username_field"]] = username
        data[form_info["password_field"]] = password

        try:
            resp = self.session.post(form_info["action"], data=data, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            # Look for error messages
            for cls in ["error", "alert", "warning", "message", "flash", "notification"]:
                el = soup.find(class_=lambda c: c and cls in c.lower() if c else False)
                if el:
                    return el.get_text(strip=True)
        except Exception:
            pass
        return ""
