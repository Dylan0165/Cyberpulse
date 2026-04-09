"""Module 13 — CSRF (Cross-Site Request Forgery) Detection.

Checks forms for CSRF token presence and validates token implementation.
"""

import json
import logging
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m13")

CSRF_TOKEN_NAMES = [
    "csrf_token", "csrftoken", "csrf", "_csrf", "__csrf",
    "csrfmiddlewaretoken", "authenticity_token", "_token",
    "anti-csrf-token", "antiforgery", "__requestverificationtoken",
    "x-csrf-token", "x-xsrf-token",
]


class Scanner:
    name = "CSRF Detection"
    phase = "vulnerability_scan"
    description = "Checks forms for missing CSRF protection tokens"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"CSRF detection for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Crawl for forms
        pages_to_check = [base_url]
        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full = urljoin(base_url, href)
                if self.target in full and full not in pages_to_check:
                    pages_to_check.append(full)
        except Exception:
            pass

        pages_to_check = pages_to_check[:20]  # Limit crawling
        raw_lines.append(f"Checking {len(pages_to_check)} pages for forms")

        total_forms = 0
        vulnerable_forms = 0

        for page_url in pages_to_check:
            try:
                resp = self.session.get(page_url, timeout=8)
                soup = BeautifulSoup(resp.text, "html.parser")

                for form in soup.find_all("form"):
                    method = form.get("method", "GET").upper()
                    if method == "GET":
                        continue  # GET forms don't need CSRF protection

                    total_forms += 1
                    action = form.get("action", "")
                    form_url = urljoin(page_url, action) if action else page_url

                    # Check for CSRF token in form fields
                    has_csrf = False
                    for inp in form.find_all("input", {"type": "hidden"}):
                        name = (inp.get("name") or "").lower()
                        if any(token_name in name for token_name in CSRF_TOKEN_NAMES):
                            has_csrf = True
                            value = inp.get("value", "")
                            raw_lines.append(f"  [OK] {form_url} — CSRF token present ({name})")

                            # Validate token quality
                            if len(value) < 16:
                                findings.append({
                                    "type": "weak_csrf_token",
                                    "url": form_url,
                                    "token_name": name,
                                    "token_length": len(value),
                                    "detail": f"CSRF token is only {len(value)} chars (should be >= 32)",
                                    "severity": "medium",
                                })
                            break

                    if not has_csrf:
                        # Also check meta tags for CSRF
                        meta_csrf = False
                        for meta in soup.find_all("meta"):
                            name = (meta.get("name") or "").lower()
                            if any(t in name for t in CSRF_TOKEN_NAMES):
                                meta_csrf = True
                                break

                        if not meta_csrf:
                            vulnerable_forms += 1
                            raw_lines.append(f"  [!] {form_url} — NO CSRF token (method={method})")
                            findings.append({
                                "type": "missing_csrf_token",
                                "url": form_url,
                                "page": page_url,
                                "method": method,
                                "detail": f"POST form without CSRF protection at {form_url}",
                                "severity": "high",
                            })

            except Exception as e:
                raw_lines.append(f"  Error checking {page_url}: {e}")

        # Check SameSite cookie attribute
        raw_lines.append("\n[Cookie SameSite Check]")
        try:
            resp = self.session.get(base_url, timeout=8)
            for cookie in resp.cookies:
                samesite = None
                for attr in cookie._rest:
                    if "samesite" in attr.lower():
                        samesite = cookie._rest[attr]
                if samesite is None or str(samesite).lower() == "none":
                    raw_lines.append(f"  [WARN] Cookie '{cookie.name}': SameSite={samesite or 'not set'}")
                    findings.append({
                        "type": "cookie_no_samesite",
                        "cookie": cookie.name,
                        "detail": f"Cookie '{cookie.name}' has no/weak SameSite attribute",
                        "severity": "medium",
                    })
        except Exception:
            pass

        raw_lines.append(f"\nTotal POST forms: {total_forms}, Vulnerable: {vulnerable_forms}")
        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "13_csrf.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("CSRF scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}
