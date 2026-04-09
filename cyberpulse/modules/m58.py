"""M58 — HTTP Parameter Pollution."""
import requests

class Scanner:
    name = "HTTP Parameter Pollution"
    phase = "scanning"
    description = "Detect HPP vulnerabilities where duplicate parameters cause unexpected behavior."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        test_params = ["id", "user_id", "page", "sort", "filter", "category", "role", "admin"]

        endpoints = ["/", "/api/v1/users", "/search", "/products", "/profile"]

        for ep in endpoints:
            url = self.base.rstrip("/") + ep
            for param in test_params:
                try:
                    # Normal request
                    r1 = requests.get(url, params={param: "1"}, timeout=timeout, verify=False)
                    # Duplicate param
                    qs = f"{param}=1&{param}=2&{param}=admin"
                    r2 = requests.get(f"{url}?{qs}", timeout=timeout, verify=False)
                    raw.append(f"HPP {url}?{qs}: {r2.status_code}")

                    # Different status = server behaves differently with duplicate params
                    if r2.status_code != r1.status_code:
                        findings.append({
                            "type": "hpp",
                            "detail": f"HTTP Parameter Pollution: duplicate '{param}' causes status change {r1.status_code} -> {r2.status_code} at {url}",
                            "severity": "medium",
                            "url": url,
                            "param": param,
                        })
                    elif len(r2.text) != len(r1.text):
                        findings.append({
                            "type": "hpp",
                            "detail": f"HTTP Parameter Pollution: duplicate '{param}' causes response length difference at {url}",
                            "severity": "low",
                            "url": url,
                            "param": param,
                        })
                except Exception as e:
                    raw.append(f"HPP probe {ep}: {e}")

        # Test query string overriding in WAF bypass scenarios
        waf_bypass_tests = [
            ("/?id=1&id=1 OR 1=1", "SQL injection bypass via HPP"),
            ("/?id=1&id=<script>alert(1)</script>", "XSS bypass via HPP"),
        ]
        for qs, desc in waf_bypass_tests:
            try:
                r = requests.get(self.base + qs, timeout=timeout, verify=False)
                raw.append(f"WAF bypass {qs}: {r.status_code}")
                if "<script>" in r.text.lower() or "1=1" in r.text.lower():
                    findings.append({
                        "type": "hpp_waf_bypass",
                        "detail": f"Possible WAF bypass via HPP: {desc}",
                        "severity": "high",
                        "url": self.base + qs,
                    })
            except Exception as e:
                raw.append(f"WAF bypass error: {e}")

        if not any(f["type"] in ("hpp", "hpp_waf_bypass") for f in findings):
            findings.append({"type": "info", "detail": "No HTTP parameter pollution vulnerabilities detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
