"""M55 — Server-Side Template Injection (SSTI) Detection."""
import requests
import re

class Scanner:
    name = "SSTI Detection"
    phase = "exploitation"
    description = "Detect server-side template injection in Jinja2, Twig, Freemarker, Pebble, Smarty, etc."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # Math-based SSTI payloads — all should evaluate to 49
        payloads = [
            ("{{7*7}}", "49"),                          # Jinja2, Twig
            ("${7*7}", "49"),                            # Java EL / Freemarker
            ("#{7*7}", "49"),                            # Pebble / Thymeleaf
            ("<%= 7*7 %>", "49"),                        # ERB
            ("{7*7}", "49"),                             # Unknown
            ("{{7*'7'}}", "7777777"),                    # Jinja2-specific
            ("${{7*7}}", "49"),                          # Mixed
        ]

        # Parameters commonly used in templates
        params = ["name", "q", "search", "query", "message", "text", "input", "template", "id"]
        endpoints = ["/", "/search", "/profile", "/contact", "/render", "/template"]

        for ep in endpoints:
            url = self.base.rstrip("/") + ep
            for param in params:
                for pl, expected in payloads:
                    try:
                        r = requests.get(url, params={param: pl}, timeout=timeout, verify=False)
                        raw.append(f"GET {url}?{param}={pl}: {r.status_code}")
                        if expected in r.text:
                            engine = "Jinja2/Twig" if "{{" in pl else ("Freemarker/EL" if "${" in pl else "Unknown")
                            findings.append({
                                "type": "ssti",
                                "detail": f"SSTI confirmed via GET param '{param}' at {url} (engine: {engine})",
                                "severity": "critical",
                                "url": url,
                                "param": param,
                                "payload": pl,
                                "engine": engine,
                            })
                            break
                    except Exception as e:
                        raw.append(f"GET {url}: {e}")

        # POST body injection
        for ep in endpoints:
            url = self.base.rstrip("/") + ep
            for pl, expected in payloads[:3]:
                try:
                    r = requests.post(url, data={"name": pl, "q": pl}, timeout=timeout, verify=False)
                    raw.append(f"POST {url} payload {pl}: {r.status_code}")
                    if expected in r.text:
                        findings.append({
                            "type": "ssti",
                            "detail": f"SSTI confirmed via POST body at {url}",
                            "severity": "critical",
                            "url": url,
                            "payload": pl,
                        })
                        break
                except Exception as e:
                    raw.append(f"POST {url}: {e}")

        # Detect template error messages
        error_indicators = [
            "TemplateSyntaxError", "UndefinedError", "TemplateNotFound",
            "Jinja2", "Twig", "Smarty", "Freemarker", "velocity",
        ]
        try:
            r_err = requests.get(f"{self.base}/?name={{{{", timeout=timeout, verify=False)
            for ind in error_indicators:
                if ind.lower() in r_err.text.lower():
                    findings.append({
                        "type": "ssti",
                        "detail": f"Template engine error disclosed: {ind}",
                        "severity": "medium",
                        "url": self.base,
                    })
                    break
        except Exception as e:
            raw.append(f"Error probe: {e}")

        if not any(f["type"] == "ssti" and f["severity"] in ("high", "critical") for f in findings):
            findings.append({"type": "info", "detail": "No SSTI vulnerabilities detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
