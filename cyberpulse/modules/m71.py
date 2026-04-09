"""M71 — Authenticated Web Scanning (Gray Box)
Logs into the web application using provided credentials and scans authenticated pages
for vulnerabilities like IDOR, auth bypass, sensitive data exposure, and broken access control.
"""
import re
import time
import urllib.parse
import urllib.request
import urllib.error


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

    def run(self):
        findings = []
        output = []
        creds = self.creds

        username = creds.get("web_username", "")
        password = creds.get("web_password", "")
        login_url = creds.get("web_login_url", "")

        if not username or not password:
            return {"findings": [], "raw_output": "[M71] Geen web-inloggegevens opgegeven — gray box scan overgeslagen"}

        output.append(f"[M71] Authenticated web scan: {self.target_url}")
        output.append(f"  Gebruikersnaam: {username}")
        output.append(f"  Login URL: {login_url or '(auto-detect)'}")

        # Build a simple cookie jar / session via urllib
        import http.cookiejar
        cookie_jar = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))

        # -- Step 1: Try to log in --
        if not login_url:
            for path in ["/login", "/signin", "/auth", "/user/login", "/wp-login.php", "/admin"]:
                try:
                    login_url = f"{self.target_url}{path}"
                    resp = opener.open(login_url, timeout=8)
                    if resp.status == 200:
                        break
                except Exception:
                    login_url = ""

        logged_in = False
        session_cookies = {}
        if login_url:
            try:
                post_data = urllib.parse.urlencode({
                    "username": username, "password": password,
                    "user": username, "pass": password,
                    "email": username, "log": username, "pwd": password,
                }).encode()
                req = urllib.request.Request(login_url, data=post_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded",
                             "User-Agent": "CyberPulse/4.0 Security Scanner"})
                resp = opener.open(req, timeout=10)
                # Collect cookies
                for cookie in cookie_jar:
                    session_cookies[cookie.name] = cookie.value
                    if cookie.name.lower() in ("session", "sessionid", "phpsessid", "auth", "token", "jwt"):
                        logged_in = True
                        output.append(f"  [+] Login geslaagd — sessiecookie: {cookie.name}")
                        findings.append({
                            "title": "Authenticatie Bevestigd",
                            "severity": "info",
                            "description": f"Succesvol ingelogd als '{username}' via {login_url}",
                            "recommendation": "Zorg dat sessiecookies HTTPOnly en Secure zijn"
                        })
            except Exception as e:
                output.append(f"  [-] Login mislukt: {e}")

        # -- Step 2: Scan authenticated pages --
        auth_paths = ["/dashboard", "/admin", "/profile", "/account", "/settings",
                      "/api/user", "/api/users", "/api/admin", "/user/1", "/user/2",
                      "/admin/users", "/admin/config", "/manage", "/panel"]
        cookie_header = "; ".join(f"{k}={v}" for k, v in session_cookies.items())

        for path in auth_paths:
            try:
                url = f"{self.target_url}{path}"
                req = urllib.request.Request(url, headers={
                    "Cookie": cookie_header,
                    "User-Agent": "CyberPulse/4.0 Security Scanner"
                })
                resp = opener.open(req, timeout=6)
                body = resp.read(4096).decode("utf-8", errors="ignore")
                status = resp.status
                output.append(f"  [{status}] {path}")

                if status == 200:
                    sensitive_patterns = [
                        (r"password", "Mogelijke wachtwoord-veld zichtbaar in authenticated pagina"),
                        (r"api.?key|secret|token", "API sleutel of token zichtbaar in response"),
                        (r"<input.*?type=[\"']password", "Wachtwoordveld gevonden in authenticated pagina"),
                        (r"SELECT.*FROM|INSERT INTO|mysql_", "Mogelijke SQL-fout of query in response"),
                    ]
                    for pattern, desc in sensitive_patterns:
                        if re.search(pattern, body, re.IGNORECASE):
                            findings.append({
                                "title": f"Gevoelige Data in Authenticated Pagina: {path}",
                                "severity": "high",
                                "description": f"{desc} op {url}",
                                "recommendation": "Verwijder gevoelige informatie uit responses. Versleutel API-sleutels en tokens."
                            })
            except urllib.error.HTTPError as e:
                output.append(f"  [{e.code}] {path}")
            except Exception:
                pass
            time.sleep(0.3)

        # -- Step 3: IDOR test --
        idor_paths = ["/user/1", "/user/2", "/api/user/1", "/api/user/2",
                      "/account/1", "/account/2", "/profile/1", "/profile/2"]
        idor_found = []
        for path in idor_paths:
            try:
                url = f"{self.target_url}{path}"
                req = urllib.request.Request(url, headers={
                    "Cookie": cookie_header,
                    "User-Agent": "CyberPulse/4.0 Security Scanner"
                })
                resp = opener.open(req, timeout=6)
                if resp.status == 200:
                    idor_found.append(path)
                    output.append(f"  [IDOR?] {path} — HTTP 200 toegankelijk")
            except Exception:
                pass

        if len(idor_found) >= 2:
            findings.append({
                "title": "Mogelijk IDOR (Insecure Direct Object Reference)",
                "severity": "high",
                "description": f"Meerdere gebruikers/object-paden toegankelijk: {', '.join(idor_found[:5])}. Mogelijk kunnen andere gebruikersprofielen worden bekeken.",
                "recommendation": "Implementeer object-level autorisatiecontroles. Gebruik UUID's in plaats van oplopende nummers. Valideer altijd dat de ingelogde gebruiker eigenaar is van het opgevraagde object."
            })

        if not findings:
            output.append("  [OK] Geen authenticatie-gerelateerde kwetsbaarheden gevonden")

        return {"findings": findings, "raw_output": "\n".join(output)}
