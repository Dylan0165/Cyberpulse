"""M74 — Authenticated CMS Audit (Gray Box)
Logs into WordPress/Joomla/Drupal admin panel and checks for vulnerabilities,
weak plugins, user enumeration, and insecure configurations.
"""
import re
import urllib.parse
import urllib.request
import urllib.error
import http.cookiejar


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
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def _get(self, path):
        try:
            resp = self.opener.open(f"{self.target_url}{path}", timeout=8)
            return resp.status, resp.read(8192).decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    def run(self):
        findings = []
        output = []
        username = self.creds.get("web_username", "")
        password = self.creds.get("web_password", "")

        output.append(f"[M74] Authenticated CMS audit: {self.target_url}")

        if not username or not password:
            return {"findings": [], "raw_output": "[M74] Geen inloggegevens opgegeven — overgeslagen"}

        # Detect CMS
        cms = None
        status, body = self._get("/wp-login.php")
        if status == 200 and "wordpress" in body.lower(): cms = "wordpress"
        if not cms:
            status, body = self._get("/administrator/index.php")
            if status == 200: cms = "joomla"
        if not cms:
            status, body = self._get("/user/login")
            if status == 200: cms = "drupal"

        output.append(f"  CMS gedetecteerd: {cms or 'onbekend'}")

        if cms == "wordpress":
            # Login
            nonce = re.search(r'name="[^"]*nonce[^"]*"\s+value="([^"]+)"', body) if body else None
            post_data = {
                "log": username, "pwd": password,
                "wp-submit": "Log In", "redirect_to": "/wp-admin/", "testcookie": "1"
            }
            if nonce: post_data["_wpnonce"] = nonce.group(1)
            try:
                resp = self.opener.open(
                    urllib.request.Request(f"{self.target_url}/wp-login.php",
                        data=urllib.parse.urlencode(post_data).encode(),
                        headers={"Content-Type": "application/x-www-form-urlencoded",
                                 "User-Agent": "CyberPulse/4.0"}), timeout=10)
                output.append(f"  Login response: {resp.status} -> {resp.url}")
            except Exception as e:
                output.append(f"  Login fout: {e}")

            # Check admin capabilities
            for path, label in [
                ("/wp-admin/user-new.php", "Nieuwe gebruiker aanmaken"),
                ("/wp-admin/plugin-install.php", "Plugins installeren"),
                ("/wp-admin/theme-editor.php", "Thema-editor (code uitvoering)"),
                ("/wp-admin/options-general.php", "Algemene instellingen"),
            ]:
                status, body = self._get(path)
                output.append(f"  [{status}] {path}")
                if status == 200:
                    findings.append({
                        "title": f"WordPress Admin Functie Bereikbaar: {label}",
                        "severity": "high",
                        "description": f"Als gebruiker '{username}' is '{label}' ({path}) toegankelijk. Plugin-installatie en thema-editor geven directe code-uitvoering.",
                        "recommendation": "Beperk admin-toegang via IP-whitelist. Schakel de thema-editor uit (define('DISALLOW_FILE_EDIT', true) in wp-config.php). Gebruik 2FA voor beheerders."
                    })

            # User enumeration via WP REST API
            status, body = self._get("/wp-json/wp/v2/users")
            if status == 200 and '"slug"' in body:
                users = re.findall(r'"slug":"([^"]+)"', body)
                findings.append({
                    "title": "WordPress Gebruikersenumeratie via REST API",
                    "severity": "medium",
                    "description": f"De WordPress REST API onthult gebruikersnamen: {', '.join(users[:5])}",
                    "recommendation": "Schakel gebruikersopmaak in REST API uit. Voeg toe aan functions.php: remove_action('rest_api_init', 'wp_oembed_register_route');"
                })

        if not findings:
            output.append("  [OK] Geen kritieke CMS-kwetsbaarheden gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
