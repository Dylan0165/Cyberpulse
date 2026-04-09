"""M52 — Web Cache Poisoning Detection."""
import requests
import re

class Scanner:
    name = "Web Cache Poisoning"
    phase = "exploitation"
    description = "Detect web cache poisoning via unkeyed headers and cache deception."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)
        canary = "cyberpulse-cache-test-xq9z"

        unkeyed_headers = [
            ("X-Forwarded-Host", f"{canary}.attacker.com"),
            ("X-Forwarded-Scheme", "nothttps"),
            ("X-Original-URL", f"/{canary}"),
            ("X-Rewrite-URL", f"/{canary}"),
            ("X-Host", f"{canary}.attacker.com"),
            ("X-Forwarded-Server", f"{canary}.evil.com"),
        ]

        try:
            baseline = requests.get(self.base, timeout=timeout, verify=False)
            raw.append(f"Baseline: {baseline.status_code}")
        except Exception as e:
            return {"findings": [{"type": "error", "detail": str(e), "severity": "info"}], "raw_output": str(e)}

        cache_headers = ["X-Cache", "CF-Cache-Status", "Age", "X-Varnish", "Via", "X-Cache-Status"]
        cached = any(h.lower() in {k.lower() for k in baseline.headers} for h in cache_headers)
        if cached:
            raw.append("Caching layer detected")
            findings.append({"type": "info", "detail": "Caching layer confirmed — cache poisoning risk exists", "severity": "info"})

        for header, value in unkeyed_headers:
            try:
                r = requests.get(self.base, headers={header: value}, timeout=timeout, verify=False)
                raw.append(f"{header}: {r.status_code}")
                if canary.lower() in r.text.lower():
                    findings.append({
                        "type": "cache_poisoning",
                        "detail": f"Unkeyed header reflected in response: {header}: {value}",
                        "severity": "critical",
                        "url": self.base,
                        "header": header,
                    })
                    break
            except Exception as e:
                raw.append(f"{header} error: {e}")

        # Cache deception paths
        deception_paths = [
            f"/account{'/'}robots.txt",
            f"/profile{'/'}style.css",
            f"/dashboard{'/'}favicon.ico",
        ]
        for path in deception_paths:
            try:
                r = requests.get(self.base.rstrip("/") + path, timeout=timeout, verify=False)
                raw.append(f"Deception path {path}: {r.status_code}")
                if r.status_code == 200 and any(h.lower() in {k.lower() for k in r.headers} for h in cache_headers):
                    findings.append({
                        "type": "cache_deception",
                        "detail": f"Potential cache deception: authenticated path served with caching on {path}",
                        "severity": "high",
                        "url": self.base + path,
                    })
            except Exception as e:
                raw.append(f"Deception {path}: {e}")

        if not any(f["type"] in ("cache_poisoning", "cache_deception") for f in findings):
            findings.append({"type": "info", "detail": "No cache poisoning vulnerabilities detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
