"""Module 15 — Open Redirect Detection.

Tests for open redirect vulnerabilities in URL parameters.
"""

import json
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m15")

# Parameters commonly used for redirects
REDIRECT_PARAMS = [
    "url", "redirect", "redirect_url", "redirect_uri", "return",
    "return_url", "returnurl", "returnto", "return_to", "next",
    "next_url", "redir", "goto", "dest", "destination", "continue",
    "target", "link", "forward", "out", "view", "ref", "callback",
    "checkout_url", "return_path", "success_url", "error_url",
]

# Test payloads
REDIRECT_PAYLOADS = [
    "https://evil.com",
    "//evil.com",
    "/\\evil.com",
    "https://evil.com%23.{target}",
    "https://{target}.evil.com",
    "https://evil.com?{target}",
    "https://evil.com#{target}",
    "/%09/evil.com",
    "/%5cevil.com",
    "/evil.com",
    "https:evil.com",
]


class Scanner:
    name = "Open Redirect Detection"
    phase = "vulnerability_scan"
    description = "Tests for open redirect vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Open redirect detection for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Find existing redirect parameters in the site
        discovered_params = self._discover_redirect_params(base_url)
        raw_lines.append(f"Discovered {len(discovered_params)} URLs with redirect params")

        # Test discovered parameters
        for disc in discovered_params:
            url = disc["url"]
            param = disc["param"]
            raw_lines.append(f"\n[Testing] {url} — param: {param}")

            for payload_template in REDIRECT_PAYLOADS:
                payload = payload_template.replace("{target}", self.target)
                try:
                    resp = self.session.get(
                        url,
                        params={param: payload},
                        allow_redirects=False,
                        timeout=8,
                    )

                    if resp.status_code in (301, 302, 303, 307, 308):
                        location = resp.headers.get("Location", "")
                        if self._is_external_redirect(location):
                            raw_lines.append(f"  [!] Redirect to: {location}")
                            findings.append({
                                "type": "open_redirect",
                                "url": url,
                                "parameter": param,
                                "payload": payload,
                                "redirect_to": location,
                                "status_code": resp.status_code,
                                "severity": "medium",
                            })
                            break  # One finding per param
                except Exception:
                    pass

        # Test common paths with redirect params
        raw_lines.append("\n[Testing common redirect paths]")
        common_paths = [
            "login", "logout", "signin", "signout", "auth",
            "oauth", "sso", "redirect", "external",
        ]

        for path in common_paths:
            url = f"{base_url}/{path}"
            for param in REDIRECT_PARAMS[:8]:  # Test first 8 params
                for payload_template in REDIRECT_PAYLOADS[:3]:  # First 3 payloads
                    payload = payload_template.replace("{target}", self.target)
                    try:
                        resp = self.session.get(
                            url,
                            params={param: payload},
                            allow_redirects=False,
                            timeout=5,
                        )
                        if resp.status_code in (301, 302, 303, 307, 308):
                            location = resp.headers.get("Location", "")
                            if self._is_external_redirect(location):
                                raw_lines.append(f"  [!] {url}?{param}={payload} -> {location}")
                                findings.append({
                                    "type": "open_redirect",
                                    "url": url,
                                    "parameter": param,
                                    "payload": payload,
                                    "redirect_to": location,
                                    "severity": "medium",
                                })
                                break
                    except Exception:
                        pass

        if not findings:
            raw_lines.append("\nNo open redirect vulnerabilities detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "15_redirect.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Open redirect scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _discover_redirect_params(self, base_url: str) -> list[dict]:
        """Find URLs that already use redirect-like parameters."""
        discovered = []
        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.query:
                    params = parse_qs(parsed.query)
                    for param_name in params:
                        if param_name.lower() in REDIRECT_PARAMS:
                            discovered.append({
                                "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                                "param": param_name,
                            })
        except Exception:
            pass
        return discovered[:20]

    def _is_external_redirect(self, location: str) -> bool:
        """Check if a redirect location points to an external domain."""
        if not location:
            return False
        try:
            parsed = urlparse(location)
            if parsed.netloc and self.target not in parsed.netloc:
                return True
            if location.startswith("//") and self.target not in location:
                return True
        except Exception:
            pass
        return False
