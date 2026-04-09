"""Module 16 — Sensitive Data Exposure.

Scans for exposed sensitive data like API keys, passwords, tokens, emails,
and private information in HTML, JavaScript, and common files.
"""

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m16")

# Regex patterns for sensitive data
SENSITIVE_PATTERNS = [
    ("API Key (Generic)", r"""(?:api[_-]?key|apikey)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{20,})['"]"""),
    ("AWS Access Key", r"""AKIA[0-9A-Z]{16}"""),
    ("AWS Secret Key", r"""(?:aws_secret|secret_key)\s*[:=]\s*['"]([a-zA-Z0-9/+=]{40})['"]"""),
    ("Google API Key", r"""AIza[0-9A-Za-z\-_]{35}"""),
    ("Slack Token", r"""xox[bpors]-[0-9a-zA-Z]{10,48}"""),
    ("GitHub Token", r"""(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,}"""),
    ("JWT Token", r"""eyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+"""),
    ("Private Key", r"""-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----"""),
    ("Password in URL", r"""(?:password|passwd|pwd)\s*[:=]\s*['"]([^'"]{4,})['"]"""),
    ("Database URL", r"""(?:mysql|postgres|mongodb|redis)://[^\s'"]+"""),
    ("Email Address", r"""[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"""),
    ("IP Address (Internal)", r"""(?:10\.\d{1,3}\.\d{1,3}\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3}|192\.168\.\d{1,3}\.\d{1,3})"""),
    ("Bearer Token", r"""[Bb]earer\s+[a-zA-Z0-9_\-\.]{20,}"""),
    ("Basic Auth", r"""[Bb]asic\s+[A-Za-z0-9+/=]{20,}"""),
    ("Stripe Key", r"""(?:sk_live|pk_live|sk_test|pk_test)_[0-9a-zA-Z]{24,}"""),
    ("Mailgun Key", r"""key-[0-9a-zA-Z]{32}"""),
    ("Twilio", r"""SK[0-9a-fA-F]{32}"""),
    ("SendGrid", r"""SG\.[a-zA-Z0-9_-]{22}\.[a-zA-Z0-9_-]{43}"""),
    ("Firebase URL", r"""https://[a-z0-9-]+\.firebaseio\.com"""),
]

# Files that commonly contain sensitive data
SENSITIVE_FILES = [
    "robots.txt", ".env", "config.js", "config.json",
    "app.js", "main.js", "bundle.js", "wp-config.php",
    ".git/config", "package.json", "composer.json",
]


class Scanner:
    name = "Sensitive Data Exposure"
    phase = "vulnerability_scan"
    description = "Scans for exposed API keys, passwords, tokens, and sensitive data"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Sensitive data exposure scan for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Scan main page
        self._scan_url(base_url, findings, raw_lines)

        # Scan JavaScript files
        raw_lines.append("\n[JavaScript Files]")
        js_urls = self._find_js_files(base_url)
        raw_lines.append(f"Found {len(js_urls)} JavaScript files")
        for js_url in js_urls[:15]:
            self._scan_url(js_url, findings, raw_lines)

        # Check common sensitive files
        raw_lines.append("\n[Common Sensitive Files]")
        for filename in SENSITIVE_FILES:
            url = f"{base_url}/{filename}"
            try:
                resp = self.session.get(url, timeout=5)
                if resp.status_code == 200 and len(resp.text) > 10:
                    raw_lines.append(f"  [FOUND] {filename} (status 200)")
                    findings.append({
                        "type": "exposed_file",
                        "url": url,
                        "filename": filename,
                        "severity": "high" if filename in (".env", ".git/config", "wp-config.php") else "medium",
                    })
                    self._scan_content(resp.text, url, findings, raw_lines)
            except Exception:
                pass

        # Check HTML comments for sensitive info
        raw_lines.append("\n[HTML Comments]")
        try:
            resp = self.session.get(base_url, timeout=10)
            comments = re.findall(r"<!--(.*?)-->", resp.text, re.DOTALL)
            for comment in comments:
                comment = comment.strip()
                if len(comment) > 10:
                    # Check for sensitive content in comments
                    for name, pattern in SENSITIVE_PATTERNS[:6]:
                        if re.search(pattern, comment, re.IGNORECASE):
                            raw_lines.append(f"  [!] Sensitive data in comment: {name}")
                            findings.append({
                                "type": "sensitive_comment",
                                "detail": f"HTML comment contains {name}",
                                "severity": "high",
                            })
                    # Check for TODO/FIXME with sensitive info
                    if re.search(r"(?:TODO|FIXME|HACK|password|secret|key|token)", comment, re.IGNORECASE):
                        raw_lines.append(f"  [WARN] Interesting comment: {comment[:80]}")
                        findings.append({
                            "type": "interesting_comment",
                            "comment": comment[:200],
                            "severity": "low",
                        })
        except Exception:
            pass

        if not findings:
            raw_lines.append("\nNo sensitive data exposure detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "16_sensitive_data.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Sensitive data scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _scan_url(self, url: str, findings: list, raw_lines: list):
        """Scan a URL's content for sensitive data."""
        try:
            resp = self.session.get(url, timeout=10)
            self._scan_content(resp.text, url, findings, raw_lines)
        except Exception:
            pass

    def _scan_content(self, content: str, source_url: str, findings: list, raw_lines: list):
        """Scan text content for sensitive patterns."""
        for name, pattern in SENSITIVE_PATTERNS:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                # Skip common false positives for emails
                if name == "Email Address":
                    matches = [m for m in matches if not m.endswith((".png", ".jpg", ".gif", ".css", ".js"))]
                    if len(matches) > 10:
                        matches = matches[:10]

                if matches:
                    raw_lines.append(f"  [{name}] {len(matches)} match(es) in {source_url}")
                    severity = "critical" if "key" in name.lower() or "private" in name.lower() or "password" in name.lower() else "medium"
                    findings.append({
                        "type": "sensitive_data",
                        "pattern_name": name,
                        "source_url": source_url,
                        "match_count": len(matches),
                        "severity": severity,
                    })

    def _find_js_files(self, base_url: str) -> list[str]:
        """Find JavaScript file URLs from the main page."""
        js_urls = []
        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for script in soup.find_all("script", src=True):
                src = script["src"]
                full_url = urljoin(base_url, src)
                if full_url.startswith(("http://", "https://")):
                    js_urls.append(full_url)
        except Exception:
            pass
        return js_urls
