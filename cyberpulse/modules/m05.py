"""Module 05 — Technology Detection (Wappalyzer-style).

Identifies web technologies, frameworks, CMS, and libraries by inspecting
HTTP headers, HTML content, cookies, and JavaScript globals.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m05")

# Technology signatures: (name, category, patterns)
SIGNATURES = [
    # CMS
    ("WordPress", "CMS", {"html": [r"wp-content", r"wp-includes", r"wp-json"], "headers": {"x-powered-by": r"wordpress"}}),
    ("Joomla", "CMS", {"html": [r"/media/jui/", r"Joomla!", r"/administrator/"]}),
    ("Drupal", "CMS", {"html": [r"Drupal\.settings", r"sites/default/files", r'name="Generator" content="Drupal']}),
    ("Magento", "CMS", {"html": [r"Mage\.Cookies", r"/skin/frontend/", r"magento"]}),
    # Frameworks
    ("React", "JS Framework", {"html": [r"__NEXT_DATA__", r"_reactRootContainer", r"react\.production"]}),
    ("Angular", "JS Framework", {"html": [r"ng-version", r"ng-app", r"angular\.min\.js"]}),
    ("Vue.js", "JS Framework", {"html": [r"__vue__", r"vue\.min\.js", r"vue\.runtime"]}),
    ("Next.js", "Framework", {"html": [r"__NEXT_DATA__", r"_next/static"], "headers": {"x-powered-by": r"Next\.js"}}),
    ("Nuxt.js", "Framework", {"html": [r"__NUXT__", r"_nuxt/"]}),
    ("Laravel", "Framework", {"cookies": [r"laravel_session"], "headers": {"x-powered-by": r"Laravel"}}),
    ("Django", "Framework", {"cookies": [r"csrftoken"], "headers": {"x-frame-options": r"DENY"}}),
    ("Express", "Framework", {"headers": {"x-powered-by": r"Express"}}),
    # Servers
    ("Nginx", "Web Server", {"headers": {"server": r"nginx"}}),
    ("Apache", "Web Server", {"headers": {"server": r"Apache"}}),
    ("IIS", "Web Server", {"headers": {"server": r"Microsoft-IIS"}}),
    ("LiteSpeed", "Web Server", {"headers": {"server": r"LiteSpeed"}}),
    # Security
    ("Cloudflare", "CDN/WAF", {"headers": {"server": r"cloudflare", "cf-ray": r"."}}),
    ("AWS ELB", "CDN", {"headers": {"server": r"awselb"}}),
    # Analytics
    ("Google Analytics", "Analytics", {"html": [r"google-analytics\.com/analytics", r"gtag/js", r"UA-\d+"]}),
    ("Google Tag Manager", "Analytics", {"html": [r"googletagmanager\.com"]}),
    # Libraries
    ("jQuery", "JS Library", {"html": [r"jquery[\.-](\d+\.[\d.]+)", r"jquery\.min\.js"]}),
    ("Bootstrap", "CSS Framework", {"html": [r"bootstrap\.min\.(css|js)", r"bootstrap[\.-](\d+)"]}),
    ("Tailwind CSS", "CSS Framework", {"html": [r"tailwindcss", r"tailwind\.min\.css"]}),
    # Security headers presence detection
    ("PHP", "Language", {"headers": {"x-powered-by": r"PHP"}}),
    ("ASP.NET", "Language", {"headers": {"x-powered-by": r"ASP\.NET", "x-aspnet-version": r"."}}),
]


class Scanner:
    name = "Technology Detection"
    phase = "reconnaissance"
    description = "Identifies web technologies, frameworks, and libraries"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Technology detection for {self.target}"]
        detected = []

        urls = [f"https://{self.target}", f"http://{self.target}"]

        for url in urls:
            try:
                resp = requests.get(
                    url,
                    timeout=10,
                    allow_redirects=True,
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberPulse/1.0"},
                    verify=False,
                )
                raw_lines.append(f"\n[{url}] Status: {resp.status_code}")

                html = resp.text[:100_000]  # Limit to 100KB
                headers = {k.lower(): v for k, v in resp.headers.items()}
                cookies = {c.name: c.value for c in resp.cookies}

                for tech_name, category, patterns in SIGNATURES:
                    if self._match(patterns, html, headers, cookies):
                        if tech_name not in [d["technology"] for d in detected]:
                            version = self._extract_version(patterns, html, headers)
                            entry = {
                                "technology": tech_name,
                                "category": category,
                                "version": version,
                                "source_url": url,
                            }
                            detected.append(entry)
                            raw_lines.append(f"  [{category}] {tech_name}{' v' + version if version else ''}")

                # Check security headers
                security_headers = {
                    "strict-transport-security": "HSTS",
                    "content-security-policy": "CSP",
                    "x-content-type-options": "X-Content-Type-Options",
                    "x-frame-options": "X-Frame-Options",
                    "x-xss-protection": "X-XSS-Protection",
                    "referrer-policy": "Referrer-Policy",
                    "permissions-policy": "Permissions-Policy",
                }

                raw_lines.append("\n[Security Headers]")
                for header, name in security_headers.items():
                    present = header in headers
                    raw_lines.append(f"  {name}: {'present' if present else 'MISSING'}")
                    if not present:
                        findings.append({
                            "type": "missing_security_header",
                            "header": name,
                            "severity": "medium" if header in ("strict-transport-security", "content-security-policy") else "low",
                        })

                break  # Only need one successful request
            except requests.RequestException as e:
                raw_lines.append(f"\n[{url}] Error: {e}")

        # Add technology findings
        for tech in detected:
            findings.append({
                "type": "technology_detected",
                "technology": tech["technology"],
                "category": tech["category"],
                "version": tech["version"],
                "severity": "info",
            })

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "05_technology.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "technologies": detected}, f, indent=2)

        logger.info("Tech detection %s: %d technologies found", self.target, len(detected))
        return {"findings": findings, "raw_output": raw_output}

    @staticmethod
    def _match(patterns: dict, html: str, headers: dict, cookies: dict) -> bool:
        for h_pattern in patterns.get("html", []):
            if re.search(h_pattern, html, re.IGNORECASE):
                return True
        for header_name, h_pattern in patterns.get("headers", {}).items():
            val = headers.get(header_name, "")
            if re.search(h_pattern, val, re.IGNORECASE):
                return True
        for c_pattern in patterns.get("cookies", []):
            for cookie_name in cookies:
                if re.search(c_pattern, cookie_name, re.IGNORECASE):
                    return True
        return False

    @staticmethod
    def _extract_version(patterns: dict, html: str, headers: dict) -> str:
        # Try to extract version from patterns with capture groups
        for h_pattern in patterns.get("html", []):
            m = re.search(h_pattern, html, re.IGNORECASE)
            if m and m.groups():
                return m.group(1)
        for header_name, h_pattern in patterns.get("headers", {}).items():
            val = headers.get(header_name, "")
            m = re.search(r"[\d]+\.[\d.]+", val)
            if m:
                return m.group(0)
        return ""
