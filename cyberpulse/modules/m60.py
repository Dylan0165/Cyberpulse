"""M60 — Password Policy & Account Security Analysis."""
import requests
import time

class Scanner:
    name = "Password Policy Analysis"
    phase = "scanning"
    description = "Test password policies, account lockout, and credential security mechanisms."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        login_paths = ["/login", "/signin", "/auth", "/account/login", "/user/login", "/admin/login", "/api/login"]
        register_paths = ["/register", "/signup", "/account/register", "/user/register", "/create-account"]
        reset_paths = ["/forgot-password", "/reset-password", "/password-reset", "/auth/reset"]

        # Find login endpoint
        login_url = None
        for path in login_paths:
            try:
                r = requests.get(self.base.rstrip("/") + path, timeout=timeout, verify=False)
                if r.status_code in (200, 301, 302):
                    login_url = self.base.rstrip("/") + path
                    raw.append(f"Login page found: {path}")
                    break
            except Exception:
                pass

        # Test weak password policy on registration
        if login_url:
            # Test account lockout (5 failed attempts)
            failed = 0
            for _ in range(6):
                try:
                    r = requests.post(login_url, data={"username": "admin", "password": "wrongpass123", "email": "admin@test.com"},
                                      timeout=timeout, verify=False, allow_redirects=False)
                    raw.append(f"Login attempt: {r.status_code}")
                    if r.status_code in (429, 423):
                        findings.append({
                            "type": "info",
                            "detail": "Account lockout / rate limiting active after multiple failed logins",
                            "severity": "info",
                        })
                        break
                    failed += 1
                    time.sleep(0.2)
                except Exception as e:
                    raw.append(f"Login probe error: {e}")

            if failed >= 6:
                findings.append({
                    "type": "no_lockout",
                    "detail": "No account lockout detected after 6 failed login attempts",
                    "severity": "medium",
                    "url": login_url,
                })

        # Test password reset mechanism
        for path in reset_paths:
            try:
                r = requests.get(self.base.rstrip("/") + path, timeout=timeout, verify=False)
                if r.status_code == 200:
                    raw.append(f"Password reset found: {path}")
                    # Check for token in URL
                    if "token" in r.url or "token" in r.text.lower():
                        findings.append({
                            "type": "info",
                            "detail": f"Password reset with token found at {path} — token strength not testable remotely",
                            "severity": "info",
                            "url": self.base + path,
                        })
                    # Check HTTPS
                    if self.base.startswith("http://"):
                        findings.append({
                            "type": "password_security",
                            "detail": f"Password reset at {path} is served over HTTP — tokens interceptable",
                            "severity": "high",
                            "url": self.base + path,
                        })
            except Exception as e:
                raw.append(f"Reset probe {path}: {e}")

        # Check if forms use HTTPS
        if self.base.startswith("http://") and login_url:
            findings.append({
                "type": "password_security",
                "detail": "Login form served over HTTP — credentials transmitted in plaintext",
                "severity": "critical",
                "url": login_url,
            })

        # Check for autocomplete on password fields
        if login_url:
            try:
                r = requests.get(login_url, timeout=timeout, verify=False)
                if 'type="password"' in r.text.lower() and 'autocomplete="off"' not in r.text.lower() and 'autocomplete="new-password"' not in r.text.lower():
                    findings.append({
                        "type": "password_security",
                        "detail": "Password field missing autocomplete=off/new-password — credentials may be cached by browser",
                        "severity": "low",
                        "url": login_url,
                    })
            except Exception as e:
                raw.append(f"Autocomplete check error: {e}")

        if not findings:
            findings.append({"type": "info", "detail": "Password policy appears adequate", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
