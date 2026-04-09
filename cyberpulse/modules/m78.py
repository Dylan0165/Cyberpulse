"""M78 — Privilege Escalation / Broken Access Control (Gray Box)
Tests whether regular user credentials can access admin-only endpoints,
modify their own role, or bypass authorization checks via parameter tampering.
"""
import urllib.request
import urllib.error
import urllib.parse
import http.cookiejar
import json


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})
        if not self.target.startswith(("http://", "https://")):
            self.target_url = f"https://{self.target}"
        else:
            self.target_url = self.target
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar))
        self.api_token = self.creds.get("api_token", "")
        self.api_header = self.creds.get("api_header", "Authorization")

    def _headers(self):
        h = {"User-Agent": "CyberPulse/4.0", "Content-Type": "application/json"}
        if self.api_token:
            val = self.api_token if self.api_token.startswith("Bearer ") \
                else f"Bearer {self.api_token}"
            h[self.api_header] = val
        return h

    def _req(self, method, path, body=None):
        url = f"{self.target_url}{path}"
        data = json.dumps(body).encode() if body else None
        req = urllib.request.Request(url, data=data,
            headers=self._headers(), method=method)
        try:
            resp = self.opener.open(req, timeout=8)
            return resp.status, resp.read(512).decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            return e.code, e.read(256).decode("utf-8", errors="ignore")
        except Exception:
            return 0, ""

    def run(self):
        findings = []
        output = []

        output.append(f"[M78] Privilege escalation test: {self.target_url}")

        if not self.api_token and not self.creds.get("web_username"):
            return {"findings": [], "raw_output": "[M78] Geen credentials opgegeven — overgeslagen"}

        # 1. Try role elevation via PATCH/PUT on own user
        role_payloads = [
            {"role": "admin"}, {"role": "administrator"}, {"is_admin": True},
            {"is_superuser": True}, {"permissions": ["admin"]},
            {"user_type": "admin"}, {"access_level": 99}
        ]
        user_paths = ["/api/user", "/api/v1/user", "/api/me",
                      "/api/profile", "/api/account", "/user/profile"]
        for path in user_paths:
            for payload in role_payloads[:2]:
                status, body = self._req("PATCH", path, payload)
                if status in (200, 201, 204):
                    findings.append({
                        "title": "Privilege Escalatie via Massa-Toewijzing",
                        "severity": "critical",
                        "description": f"PATCH {path} met payload {json.dumps(payload)} retourneerde HTTP {status}. Gebruiker kan mogelijk eigen rol/rechten aanpassen.",
                        "recommendation": "Gebruik een allowlist voor velden die gebruikers mogen updaten. Nooit automatisch alle request-velden op het model mappen (massa-toewijzing)."
                    })
                output.append(f"  PATCH {path} {payload} -> {status}")
                break

        # 2. Try accessing admin-only API endpoints
        admin_paths = [
            "/api/admin", "/api/v1/admin", "/api/admin/users",
            "/api/admin/config", "/api/admin/stats",
            "/api/v1/users?role=admin", "/api/management",
            "/api/backstage", "/api/internal"
        ]
        for path in admin_paths:
            status, body = self._req("GET", path)
            if status == 200:
                findings.append({
                    "title": f"Admin API Endpoint Bereikbaar als Normale Gebruiker: {path}",
                    "severity": "critical",
                    "description": f"GET {self.target_url}{path} retourneert HTTP 200 met reguliere gebruikerstoken. Broken Access Control.",
                    "recommendation": "Controleer autorisatie op elk endpoint. Gebruik role-based access control (RBAC). Valideer server-side altijd de rol van de ingelogde gebruiker."
                })
            output.append(f"  GET {path} -> {status}")

        # 3. Horizontal privilege escalation — access other users data
        for uid in ["1", "2", "admin"]:
            for path in [f"/api/users/{uid}", f"/api/v1/users/{uid}",
                          f"/api/accounts/{uid}"]:
                status, body = self._req("GET", path)
                if status == 200 and ('"email"' in body or '"username"' in body):
                    findings.append({
                        "title": f"Horizontale Privilege Escalatie: Toegang tot Gebruiker ID {uid}",
                        "severity": "high",
                        "description": f"GET {path} retourneert data van andere gebruiker (ID {uid}) met de huidige sessie. Dit is IDOR / Broken Access Control.",
                        "recommendation": "Controleer altijd of de ingelogde gebruiker de eigenaar is van het opgevraagde object. Gebruik indirect object references."
                    })
                    break

        if not findings:
            output.append("  [OK] Geen privilege escalatie kwetsbaarheden gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
