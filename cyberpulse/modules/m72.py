"""M72 — Authenticated API Testing (Gray Box)
Tests API endpoints with provided bearer token / API key, checks for broken auth,
mass assignment, rate limiting, and excessive data exposure.
"""
import json
import time
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

    def _req(self, url, method="GET", data=None, extra_headers=None):
        headers = {"User-Agent": "CyberPulse/4.0", "Accept": "application/json"}
        token = self.creds.get("api_token", "")
        header_name = self.creds.get("api_header", "Authorization")
        if token:
            headers[header_name] = f"Bearer {token}" if not token.startswith("Bearer") else token
        if extra_headers:
            headers.update(extra_headers)
        body = json.dumps(data).encode() if data else None
        if body:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=8)
            return resp.status, resp.read(8192).decode("utf-8", errors="ignore")
        except urllib.error.HTTPError as e:
            return e.code, ""
        except Exception:
            return 0, ""

    def run(self):
        findings = []
        output = []
        token = self.creds.get("api_token", "")

        if not token:
            return {"findings": [], "raw_output": "[M72] Geen API token opgegeven — overgeslagen"}

        output.append(f"[M72] Authenticated API scan: {self.target_url}")

        # 1. Common API paths
        api_paths = ["/api", "/api/v1", "/api/v2", "/api/users", "/api/admin",
                     "/api/config", "/api/settings", "/graphql", "/api/me",
                     "/api/keys", "/api/tokens", "/api/debug", "/api/health",
                     "/v1/users", "/v2/admin"]

        accessible = []
        for path in api_paths:
            url = f"{self.target_url}{path}"
            status, body = self._req(url)
            output.append(f"  [{status}] {path}")
            if status == 200:
                accessible.append((path, body))
                # Check for excessive data exposure
                if len(body) > 2000:
                    try:
                        parsed = json.loads(body)
                        if isinstance(parsed, list) and len(parsed) > 10:
                            findings.append({
                                "title": "Excessive Data Exposure in API",
                                "severity": "high",
                                "description": f"API endpoint {path} retourneert {len(parsed)} records zonder paginering of filtering. Dit kan leiden tot onbedoelde datadiefstal.",
                                "recommendation": "Implementeer paginering, filtering en veld-selectie. Geef alleen de data terug die de gebruiker nodig heeft."
                            })
                    except Exception:
                        pass

        # 2. Test without token (broken auth check)
        broken_auth = []
        for path, _ in accessible[:5]:
            url = f"{self.target_url}{path}"
            req = urllib.request.Request(url, headers={"User-Agent": "CyberPulse/4.0"})
            try:
                resp = urllib.request.urlopen(req, timeout=6)
                if resp.status == 200:
                    broken_auth.append(path)
                    output.append(f"  [!] {path} toegankelijk ZONDER token!")
            except Exception:
                pass
            time.sleep(0.2)

        if broken_auth:
            findings.append({
                "title": "Broken Authentication — API Endpoints Zonder Auth",
                "severity": "critical",
                "description": f"De volgende API endpoints zijn toegankelijk zonder token: {', '.join(broken_auth)}",
                "recommendation": "Forceer authenticatie op alle API endpoints. Gebruik middleware die elk request valideert. Implementeer JWT met expiry of OAuth2."
            })

        # 3. Mass assignment test
        for path, _ in accessible[:3]:
            if "user" in path or "account" in path or "me" in path:
                url = f"{self.target_url}{path}"
                status, _ = self._req(url, method="PUT",
                    data={"role": "admin", "is_admin": True, "permissions": ["admin", "superuser"]})
                if status in (200, 201, 204):
                    findings.append({
                        "title": "Mogelijke Mass Assignment Kwetsbaarheid",
                        "severity": "critical",
                        "description": f"PUT naar {path} met admin-velden retourneerde HTTP {status}. Server accepteert mogelijk onbedoelde velden.",
                        "recommendation": "Gebruik allowlists voor geaccepteerde velden. Blokkeer role- en permission-velden in user-update endpoints. Valideer alle invoer server-side."
                    })

        # 4. Rate limiting test
        url = f"{self.target_url}/api/login" if accessible else f"{self.target_url}/api"
        rate_ok = 0
        for _ in range(10):
            status, _ = self._req(url)
            if status != 429:
                rate_ok += 1
        if rate_ok >= 9:
            findings.append({
                "title": "Ontbrekende API Rate Limiting",
                "severity": "medium",
                "description": "10 opeenvolgende API-requests werden geaccepteerd zonder HTTP 429 (Too Many Requests). Geen zichtbare rate limiting aanwezig.",
                "recommendation": "Implementeer rate limiting per IP en per gebruiker. Gebruik token buckets. Retourneer Retry-After headers bij exceeding."
            })

        if not findings:
            output.append("  [OK] Geen kritieke API-kwetsbaarheden gevonden")

        return {"findings": findings, "raw_output": "\n".join(output)}
