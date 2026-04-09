"""Module 11 — SQL Injection Detection.

Tests common entry points for SQL injection vulnerabilities using
error-based and time-based detection techniques.
"""

import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, parse_qs, urlencode

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger("cyberpulse.modules.m11")

# SQL error patterns that indicate injection
SQL_ERRORS = [
    r"you have an error in your sql syntax",
    r"warning:.*mysql_",
    r"unclosed quotation mark",
    r"quoted string not properly terminated",
    r"pg_query\(\).*ERROR",
    r"Microsoft OLE DB Provider for SQL Server",
    r"ODBC SQL Server Driver",
    r"SQLite3::query",
    r"ORA-\d{5}",
    r"PostgreSQL.*ERROR",
    r"com\.mysql\.jdbc",
    r"org\.postgresql\.util\.PSQLException",
    r"Microsoft Access Driver",
    r"JET Database Engine",
    r"Valid MariaDB",
    r"SQL syntax.*MariaDB",
    r"supplied argument is not a valid MySQL",
]

# Test payloads (non-destructive, detection only)
TEST_PAYLOADS = [
    "'",
    "''",
    "1' OR '1'='1",
    "1 OR 1=1",
    "' OR ''='",
    "1' AND '1'='2",
    "1; SELECT 1--",
    "' UNION SELECT NULL--",
]

# Time-based payload (uses SLEEP/WAITFOR — only for confirmation)
TIME_PAYLOADS = [
    ("1' AND SLEEP(3)--", 3),
    ("1' WAITFOR DELAY '0:0:3'--", 3),
    ("1' AND pg_sleep(3)--", 3),
]


class Scanner:
    name = "SQL Injection Detection"
    phase = "vulnerability_scan"
    description = "Tests for SQL injection in forms and URL parameters"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"SQL injection detection for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Discover forms and URLs with parameters
        urls_with_params = self._discover_urls(base_url)
        raw_lines.append(f"Discovered {len(urls_with_params)} testable URLs/forms")

        for url_info in urls_with_params:
            url = url_info["url"]
            params = url_info.get("params", {})
            method = url_info.get("method", "GET")

            raw_lines.append(f"\n[Testing] {method} {url}")

            for param_name in params:
                for payload in TEST_PAYLOADS:
                    test_params = dict(params)
                    test_params[param_name] = payload

                    try:
                        if method == "GET":
                            resp = self.session.get(url, params=test_params, timeout=8)
                        else:
                            resp = self.session.post(url, data=test_params, timeout=8)

                        # Check for SQL errors in response
                        for pattern in SQL_ERRORS:
                            if re.search(pattern, resp.text, re.IGNORECASE):
                                raw_lines.append(f"  [!] SQLi found: {param_name}={payload}")
                                raw_lines.append(f"      Pattern: {pattern}")
                                findings.append({
                                    "type": "sql_injection",
                                    "url": url,
                                    "parameter": param_name,
                                    "method": method,
                                    "payload": payload,
                                    "detection": "error-based",
                                    "error_pattern": pattern,
                                    "severity": "critical",
                                })
                                break
                    except Exception:
                        pass

                # Time-based detection (only if no error-based found for this param)
                param_findings = [f for f in findings if f.get("parameter") == param_name and f.get("url") == url]
                if not param_findings:
                    for payload, delay in TIME_PAYLOADS[:1]:  # Only test first time payload
                        test_params = dict(params)
                        test_params[param_name] = payload
                        try:
                            t0 = time.time()
                            if method == "GET":
                                self.session.get(url, params=test_params, timeout=delay + 5)
                            else:
                                self.session.post(url, data=test_params, timeout=delay + 5)
                            elapsed = time.time() - t0

                            if elapsed >= delay - 0.5:
                                raw_lines.append(f"  [!] Time-based SQLi: {param_name} (delay={elapsed:.1f}s)")
                                findings.append({
                                    "type": "sql_injection",
                                    "url": url,
                                    "parameter": param_name,
                                    "method": method,
                                    "payload": payload,
                                    "detection": "time-based",
                                    "response_time": round(elapsed, 2),
                                    "severity": "critical",
                                })
                        except Exception:
                            pass

        if not findings:
            raw_lines.append("\nNo SQL injection vulnerabilities detected")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "11_sqli.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("SQLi scan %s: %d vulnerabilities", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _discover_urls(self, base_url: str) -> list[dict]:
        """Discover URLs with parameters and forms."""
        urls = []

        try:
            resp = self.session.get(base_url, timeout=10)
            soup = BeautifulSoup(resp.text, "html.parser")

            # Find links with query parameters
            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(base_url, href)
                parsed = urlparse(full_url)
                if parsed.query and parsed.netloc and self.target in parsed.netloc:
                    params = {k: v[0] for k, v in parse_qs(parsed.query).items()}
                    if params:
                        urls.append({
                            "url": f"{parsed.scheme}://{parsed.netloc}{parsed.path}",
                            "params": params,
                            "method": "GET",
                        })

            # Find forms
            for form in soup.find_all("form"):
                action = form.get("action", "")
                method = form.get("method", "GET").upper()
                form_url = urljoin(base_url, action) if action else base_url
                parsed = urlparse(form_url)
                if parsed.netloc and self.target in parsed.netloc:
                    params = {}
                    for inp in form.find_all(["input", "textarea", "select"]):
                        name = inp.get("name")
                        if name:
                            params[name] = inp.get("value", "test")
                    if params:
                        urls.append({"url": form_url, "params": params, "method": method})

        except Exception as e:
            logger.warning("URL discovery failed: %s", e)

        # Add common parameter patterns
        for path in ["search", "login", "page", "article", "product", "user", "id"]:
            urls.append({
                "url": f"{base_url}/{path}",
                "params": {"id": "1", "q": "test"},
                "method": "GET",
            })

        return urls[:30]  # Limit to prevent excessive testing
