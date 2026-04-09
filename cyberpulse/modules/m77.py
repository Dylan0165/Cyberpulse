"""M77 — Admin Panel Discovery & Access Control (Gray Box)
With authenticated session, tests whether administrative interfaces
are accessible to the current user (Broken Access Control).
"""
import urllib.request
import urllib.error
import http.cookiejar
import urllib.parse


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

    def _login(self):
        username = self.creds.get("web_username", "")
        password = self.creds.get("web_password", "")
        login_url = self.creds.get("web_login_url", "")
        if not username or not password:
            return False
        if not login_url:
            for path in ["/login", "/signin", "/auth", "/wp-login.php"]:
                try:
                    r = self.opener.open(f"{self.target_url}{path}", timeout=5)
                    if r.status == 200:
                        login_url = f"{self.target_url}{path}"
                        break
                except Exception:
                    continue
        if not login_url:
            return False
        data = urllib.parse.urlencode({
            "username": username, "password": password,
            "email": username, "log": username, "pwd": password
        }).encode()
        try:
            self.opener.open(urllib.request.Request(
                login_url, data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded",
                         "User-Agent": "CyberPulse/4.0"}), timeout=10)
            return len(list(self.jar)) > 0
        except Exception:
            return False

    def _get_status(self, url):
        try:
            resp = self.opener.open(urllib.request.Request(
                url, headers={"User-Agent": "CyberPulse/4.0"}), timeout=6)
            body = resp.read(512).decode("utf-8", errors="ignore")
            return resp.status, body
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    ADMIN_PATHS = [
        "/admin", "/admin/", "/administrator", "/admin/dashboard",
        "/admin/users", "/admin/config", "/admin/settings",
        "/manager", "/manage", "/control", "/controlpanel",
        "/cp", "/backend", "/staff", "/superuser",
        "/phpmyadmin", "/pma", "/dbadmin",
        "/adminer", "/adminer.php",
        "/jenkins", "/sonarqube",
        "/api/admin", "/api/v1/admin",
        "/wp-admin", "/wp-admin/",
        "/joomla/administrator",
        "/kibana", "/grafana",
        "/_cat/indices", "/_cluster/health",  # Elasticsearch
    ]

    def run(self):
        findings = []
        output = []

        output.append(f"[M77] Admin panel discovery: {self.target_url}")

        logged_in = self._login()
        output.append(f"  Auth status: {'ingelogd' if logged_in else 'niet ingelogd / geen credentials'}")

        for path in self.ADMIN_PATHS:
            url = f"{self.target_url}{path}"
            status, body = self._get_status(url)
            if status == 200:
                lower_body = body.lower()
                is_admin_like = any(kw in lower_body for kw in
                    ["admin", "dashboard", "management", "configuration",
                     "phpmyadmin", "database", "users", "settings"])
                severity = "critical" if is_admin_like else "high"
                output.append(f"  [200] {path} -- admin-achtig: {is_admin_like}")
                findings.append({
                    "title": f"Admin Interface Bereikbaar: {path}",
                    "severity": severity,
                    "description": f"{'Het beheerpaneel' if is_admin_like else 'Een potentieel beheerpanel'} op {url} retourneert HTTP 200 {'met ingelogde gebruiker' if logged_in else 'zonder authenticatie'}.",
                    "recommendation": "Beperk admin-URLs via IP-whitelist of VPN. Voeg sterke authenticatie + 2FA toe. Overweeg admin-interface op apart (intern) domein of poort te zetten."
                })
            elif status in (301, 302):
                output.append(f"  [REDIRECT] {path}")
            else:
                output.append(f"  [{status}] {path}")

        if not findings:
            output.append("  [OK] Geen openstaande admin-panelen gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
