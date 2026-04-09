"""Module 12 — XSS (Cross-Site Scripting) Detection.

Tests for reflected and DOM-based XSS in parameters, forms, and headers.
"""

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m12")

# XSS test payloads with unique markers for detection
XSS_PAYLOADS = [
    {
        "payload": '<script>alert("CyberPulse")</script>',
        "detect": r'<script>alert\("CyberPulse"\)</script>',
        "type": "reflected",
    },
    {
        "payload": '"><img src=x onerror=alert(1)>',
        "detect": r'"><img src=x onerror=alert\(1\)>',
        "type": "reflected",
    },
    {
        "payload": "'-alert(1)-'",
        "detect": r"'-alert\(1\)-'",
        "type": "reflected",
    },
    {
        "payload": '<svg onload=alert(1)>',
        "detect": r'<svg onload=alert\(1\)>',
        "type": "reflected",
    },
    {
        "payload": "javascript:alert(1)",
        "detect": r"javascript:alert\(1\)",
        "type": "reflected",
    },
    {
        "payload": '"><svg/onload=alert(String.fromCharCode(88,83,83))>',
        "detect": r'<svg/onload=alert',
        "type": "reflected",
    },
    {
        "payload": "{{7*7}}",
        "detect": r"49",
        "type": "template_injection",
    },
    {
        "payload": "${7*7}",
        "detect": r"49",
        "type": "template_injection",
    },
]

# Headers to test for XSS reflection
XSS_HEADERS = ["Referer", "User-Agent", "X-Forwarded-For"]


class Scanner:
    name = "XSS Detection"
    phase = "vulnerability_scan"
    description = "Tests for reflected and DOM-based cross-site scripting"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"XSS detection for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Discover testable endpoints
        endpoints = self._discover_endpoints(base_url)
        raw_lines.append(f"Discovered {len(endpoints)} testable endpoints")

        for endpoint in endpoints:
            url = endpoint["url"]
            params = endpoint.get("params", {})
            method = endpoint.get("method", "GET")

            for param_name in params:
                for xss in XSS_PAYLOADS:
                    test_params = dict(params)
                    test_params[param_name] = xss["payload"]

                    try:
                        if method == "GET":
                            resp = self.session.get(url, params=test_params, timeout=8,
                                                     headers={"User-Agent": "Mozilla/5.0 CyberPulse/1.0"})
                        else:
                            resp = self.session.post(url, data=test_params, timeout=8,
                                                      headers={"User-Agent": "Mozilla/5.0 CyberPulse/1.0"})

                        if re.search(xss["detect"], resp.text):
                            # Verify it's in HTML context (not encoded)
                            if self._is_unencoded(xss["payload"], resp.text):
                                raw_lines.append(f"  [!] XSS ({xss['type']}): {param_name} @ {url}")
                                findings.append({
                                    "type": f"xss_{xss['type']}",
                                    "url": url,
                                    "parameter": param_name,
                                    "method": method,
                                    "payload": xss["payload"],
                                    "severity": "high",
                                })
                                break  # One finding per param is enough
                    except Exception:
                        pass

        # Check for DOM-based XSS indicators
        raw_lines.append("\n[DOM-based XSS indicators]")
        try:
            resp = self.session.get(base_url, timeout=10,
                                     headers={"User-Agent": "Mozilla/5.0 CyberPulse/1.0"})
            dom_sinks = self._check_dom_xss(resp.text)
            for sink in dom_sinks:
                raw_lines.append(f"  [WARN] {sink['detail']}")
                findings.append(sink)
        except Exception as e:
            raw_lines.append(f"  Error: {e}")

        # Test header injection
        raw_lines.append("\n[Header-based XSS]")
        for header in XSS_HEADERS:
            try:
                test_headers = {"User-Agent": "Mozilla/5.0 CyberPulse/1.0"}
                test_headers[header] = '<script>alert("XSS")</script>'
                resp = self.session.get(base_url, timeout=8, headers=test_headers)
                if '<script>alert("XSS")</script>' in resp.text:
                    raw_lines.append(f"  [!] Header XSS via {header}")
                    findings.append({
                        "type": "xss_header",
                        "header": header,
                        "url": base_url,
                        "severity": "high",
                    })
            except Exception:
                pass

        if not findings:
            raw_lines.append("\nNo XSS vulnerabilities detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "12_xss.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("XSS scan %s: %d vulnerabilities", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _is_unencoded(payload: str, response_text: str) -> bool:
        """Check if payload appears unencoded (not HTML-escaped) in response."""
        encoded_variants = [
            payload.replace("<", "&lt;").replace(">", "&gt;"),
            payload.replace('"', "&quot;"),
            payload.replace("'", "&#x27;"),
        ]
        if payload in response_text:
            for encoded in encoded_variants:
                if encoded in response_text and payload not in response_text.replace(encoded, ""):
                    return False
            return True
        return False

    @staticmethod
    def _check_dom_xss(html: str) -> list[dict]:
        """Check for DOM-based XSS sinks in JavaScript."""
        sinks = []
        dangerous_patterns = [
            (r"document\.write\s*\(", "document.write() sink"),
            (r"\.innerHTML\s*=", "innerHTML assignment"),
            (r"\.outerHTML\s*=", "outerHTML assignment"),
            (r"eval\s*\(", "eval() usage"),
            (r"setTimeout\s*\(\s*['\"]", "setTimeout with string"),
            (r"setInterval\s*\(\s*['\"]", "setInterval with string"),
            (r"location\s*=", "location assignment"),
            (r"location\.href\s*=", "location.href assignment"),
        ]

        source_patterns = [
            (r"location\.hash", "location.hash source"),
            (r"location\.search", "location.search source"),
            (r"document\.referrer", "document.referrer source"),
            (r"document\.URL", "document.URL source"),
        ]

        for pattern, desc in dangerous_patterns:
            if re.search(pattern, html):
                sinks.append({
                    "type": "dom_xss_sink",
                    "detail": f"Found {desc} in page JavaScript",
                    "pattern": pattern,
                    "severity": "medium",
                })

        for pattern, desc in source_patterns:
            if re.search(pattern, html):
                sinks.append({
                    "type": "dom_xss_source",
                    "detail": f"Found {desc} — potential DOM XSS if combined with sink",
                    "pattern": pattern,
                    "severity": "low",
                })

        return sinks

    def _discover_endpoints(self, base_url: str) -> list[dict]:
        """Discover URL parameters and forms for testing."""
        endpoints = []
        try:
            resp = self.session.get(base_url, timeout=10,
                                     headers={"User-Agent": "Mozilla/5.0 CyberPulse/1.0"})
            soup = BeautifulSoup(resp.text, "html.parser")

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.query and self.target in (parsed.netloc or ""):
                    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                    if params:
                        endpoints.append({"url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}", "params": params, "method": "GET"})

            for form in soup.find_all("form"):
                action = form.get("action", "")
                method = form.get("method", "GET").upper()
                form_url = urljoin(base_url, action) if action else base_url
                params = {}
                for inp in form.find_all(["input", "textarea"]):
                    name = inp.get("name")
                    if name:
                        params[name] = inp.get("value", "test")
                if params:
                    endpoints.append({"url": form_url, "params": params, "method": method})
        except Exception:
            pass

        # Common search/query patterns
        for path in ["search", "q", "find"]:
            endpoints.append({"url": f"{base_url}/{path}", "params": {"q": "test", "search": "test"}, "method": "GET"})

        return endpoints[:25]
