"""M57 — Open Redirect Testing."""
import requests
from urllib.parse import urlencode

class Scanner:
    name = "Open Redirect Testing"
    phase = "scanning"
    description = "Detect open redirect vulnerabilities enabling phishing attacks."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)
        evil = "https://attacker-cyberpulse.example.com"

        redirect_params = [
            "redirect", "redirect_uri", "redirect_url", "return", "returnUrl",
            "return_url", "next", "url", "goto", "rurl", "dest", "destination",
            "continue", "forward", "callback", "u", "r", "link",
        ]

        redirect_payloads = [
            evil,
            f"//{evil.split('//')[1]}",
            f"//attacker-cyberpulse.example.com",
            f"///attacker-cyberpulse.example.com",
            f"https:attacker-cyberpulse.example.com",
        ]

        endpoints = ["/", "/login", "/logout", "/auth", "/oauth", "/sso", "/redirect", "/out"]

        for ep in endpoints:
            url = self.base.rstrip("/") + ep
            for param in redirect_params:
                for payload in redirect_payloads:
                    try:
                        r = requests.get(
                            url,
                            params={param: payload},
                            timeout=timeout,
                            verify=False,
                            allow_redirects=False,
                        )
                        raw.append(f"GET {url}?{param}={payload[:30]}: {r.status_code}")
                        loc = r.headers.get("Location", "")
                        if r.status_code in (301, 302, 303, 307, 308) and (
                            "attacker-cyberpulse" in loc or "attacker-cyberpulse" in r.text
                        ):
                            findings.append({
                                "type": "open_redirect",
                                "detail": f"Open redirect via param '{param}' at {url}",
                                "severity": "medium",
                                "url": url,
                                "param": param,
                                "payload": payload,
                                "redirect_to": loc,
                            })
                    except Exception as e:
                        raw.append(f"Probe error {ep}: {e}")

        if not any(f["type"] == "open_redirect" for f in findings):
            findings.append({"type": "info", "detail": "No open redirect vulnerabilities detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
