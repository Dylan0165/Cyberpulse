"""M67 — Mobile API Endpoint Detection."""
import requests
import json

class Scanner:
    name = "Mobile API Detection"
    phase = "scanning"
    description = "Probe mobile-specific API endpoints and versioned REST paths."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        mobile_paths = [
            "/api/v1/mobile", "/api/v2/mobile", "/api/mobile",
            "/mobile/api", "/api/v1", "/api/v2", "/api/v3",
            "/api/latest", "/v1", "/v2", "/v3",
            "/api/v1/users", "/api/v1/auth", "/api/v1/login",
            "/api/v1/register", "/api/v1/profile", "/api/v1/config",
            "/api/v1/devices", "/api/v1/notifications",
            "/app/api", "/app/v1",
        ]

        mobile_agents = [
            "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
            "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
        ]

        # Probe paths with normal and mobile user agent
        exposed = []
        for path in mobile_paths:
            url = self.base.rstrip("/") + path
            for ua in [None, mobile_agents[0]]:
                headers = {"User-Agent": ua} if ua else {}
                try:
                    r = requests.get(url, headers=headers, timeout=timeout, verify=False, allow_redirects=False)
                    if r.status_code not in (404, 410, 301, 302):
                        ct = r.headers.get("Content-Type", "")
                        ua_label = "mobile-UA" if ua else "default-UA"
                        raw.append(f"{r.status_code} [{ua_label}] {url}")
                        if path not in [e[0] for e in exposed]:
                            exposed.append((path, r.status_code, ct))
                except Exception:
                    pass

        for path, code, ct in exposed:
            severity = "high" if code == 200 and "json" in ct else "medium" if code == 200 else "low"
            findings.append({
                "type": "api_exposure",
                "detail": f"Mobile/API endpoint accessible: {path} → HTTP {code} ({ct.split(';')[0]})",
                "severity": severity,
                "path": path,
                "status_code": code,
            })

        # Check for versioned API deprecation headers
        if exposed:
            sample_url = self.base.rstrip("/") + exposed[0][0]
            try:
                r = requests.get(sample_url, timeout=timeout, verify=False)
                deprecation_headers = ["deprecation", "sunset", "x-api-version", "api-version"]
                for h in deprecation_headers:
                    if h in (k.lower() for k in r.headers):
                        findings.append({
                            "type": "api_versioning",
                            "detail": f"API versioning hint header found: {h}: {r.headers.get(h, r.headers.get(h.capitalize(), ''))}",
                            "severity": "info",
                        })
            except Exception:
                pass

        # Check for JWT in mobile auth endpoints
        auth_paths = ["/api/v1/auth", "/api/v1/token", "/v1/oauth/token"]
        for path in auth_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.post(url, json={"username": "test", "password": "test"},
                                  headers={"Content-Type": "application/json"},
                                  timeout=timeout, verify=False, allow_redirects=False)
                raw.append(f"Auth probe {path}: {r.status_code}")
                if r.status_code in (200, 400, 422):
                    body = r.text[:200]
                    if "token" in body.lower() or "access_token" in body.lower():
                        findings.append({
                            "type": "jwt_endpoint",
                            "detail": f"JWT/token auth endpoint found: {path}, responds with token hints",
                            "severity": "info",
                            "path": path,
                        })
            except Exception:
                pass

        if not findings:
            findings.append({"type": "info", "detail": "No mobile API endpoints discovered", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
