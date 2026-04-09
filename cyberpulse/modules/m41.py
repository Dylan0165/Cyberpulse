"""Module 41 — Rate Limiting & DoS Resilience Testing.

Tests whether the application enforces rate limiting and is resilient
against basic denial-of-service patterns.
"""

import json
import logging
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m41")


class Scanner:
    name = "Rate Limiting & DoS Resilience"
    phase = "scanning"
    description = "Tests rate limiting enforcement and DoS resilience of the application"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Rate limiting & DoS resilience testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Login endpoint brute-force protection
        raw_lines.append("\n[Phase 1: Login Rate Limiting]")
        login_paths = ["/login", "/api/login", "/auth/login", "/signin",
                       "/api/auth/login", "/api/v1/auth/login"]
        for path in login_paths:
            url = base_url + path
            blocked = False
            responses = []
            for i in range(15):
                try:
                    resp = self.session.post(
                        url,
                        json={"username": f"testuser_{i}", "password": "wrongpass"},
                        timeout=8,
                    )
                    responses.append(resp.status_code)
                    if resp.status_code == 429:
                        blocked = True
                        raw_lines.append(f"  OK: {path} rate-limited after {i + 1} attempts")
                        break
                except Exception:
                    break

            if responses and not blocked:
                findings.append({
                    "type": "no_login_rate_limit",
                    "path": path,
                    "attempts": len(responses),
                    "detail": f"No rate limiting on {path} after {len(responses)} login attempts",
                    "severity": "high",
                })
                raw_lines.append(f"  HIGH: No rate limit on {path} ({len(responses)} attempts)")

        # Phase 2: General endpoint rate limiting
        raw_lines.append("\n[Phase 2: General Rate Limiting]")
        test_paths = ["/", "/api/", "/api/users", "/search"]
        for path in test_paths:
            url = base_url + path
            statuses = []
            start = time.time()
            for _ in range(30):
                try:
                    resp = self.session.get(url, timeout=5)
                    statuses.append(resp.status_code)
                    if resp.status_code == 429:
                        break
                except Exception:
                    break
            elapsed = time.time() - start

            rate_limited = 429 in statuses
            if not rate_limited and len(statuses) >= 25:
                findings.append({
                    "type": "no_general_rate_limit",
                    "path": path,
                    "requests_sent": len(statuses),
                    "time": f"{elapsed:.1f}s",
                    "detail": f"No rate limiting on {path} ({len(statuses)} requests in {elapsed:.1f}s)",
                    "severity": "medium",
                })
                raw_lines.append(f"  MEDIUM: No rate limit on {path}")
            elif rate_limited:
                raw_lines.append(f"  OK: {path} rate-limited after {statuses.index(429) + 1} requests")

        # Phase 3: Rate-limit header analysis
        raw_lines.append("\n[Phase 3: Rate Limit Header Analysis]")
        try:
            resp = self.session.get(base_url, timeout=10)
            rate_headers = {
                "X-RateLimit-Limit": resp.headers.get("X-RateLimit-Limit"),
                "X-RateLimit-Remaining": resp.headers.get("X-RateLimit-Remaining"),
                "X-RateLimit-Reset": resp.headers.get("X-RateLimit-Reset"),
                "Retry-After": resp.headers.get("Retry-After"),
                "RateLimit-Limit": resp.headers.get("RateLimit-Limit"),
                "RateLimit-Remaining": resp.headers.get("RateLimit-Remaining"),
            }
            found_headers = {k: v for k, v in rate_headers.items() if v}
            if found_headers:
                for header, value in found_headers.items():
                    raw_lines.append(f"  INFO: {header}: {value}")
                findings.append({
                    "type": "rate_limit_headers",
                    "headers": found_headers,
                    "detail": f"Rate limit headers present: {', '.join(found_headers.keys())}",
                    "severity": "info",
                })
            else:
                findings.append({
                    "type": "no_rate_limit_headers",
                    "detail": "No rate limit headers detected in responses",
                    "severity": "low",
                })
                raw_lines.append("  LOW: No rate limit headers found")
        except Exception:
            pass

        # Phase 4: Resource-intensive endpoint detection
        raw_lines.append("\n[Phase 4: Resource-intensive Endpoints]")
        heavy_paths = [
            "/api/search?q=" + "A" * 1000,
            "/api/export",
            "/api/report",
            "/api/users?page=1&per_page=10000",
            "/search?q=" + "test " * 100,
        ]
        for path in heavy_paths:
            url = base_url + path
            try:
                start = time.time()
                resp = self.session.get(url, timeout=15)
                elapsed = time.time() - start
                if elapsed > 5 and resp.status_code == 200:
                    findings.append({
                        "type": "slow_endpoint",
                        "path": path[:100],
                        "response_time": f"{elapsed:.1f}s",
                        "detail": f"Slow endpoint: {path[:60]} ({elapsed:.1f}s) — DoS potential",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: Slow endpoint {path[:50]} ({elapsed:.1f}s)")
            except Exception:
                continue

        # Phase 5: Large payload handling
        raw_lines.append("\n[Phase 5: Large Payload Handling]")
        large_payloads = [
            ("json", {"data": "A" * 100000}),
            ("form", "field=" + "A" * 100000),
        ]
        for label, payload in large_payloads:
            try:
                if label == "json":
                    resp = self.session.post(base_url, json=payload, timeout=15)
                else:
                    resp = self.session.post(
                        base_url,
                        data=payload,
                        headers={"Content-Type": "application/x-www-form-urlencoded"},
                        timeout=15,
                    )
                if resp.status_code not in (413, 400, 429):
                    findings.append({
                        "type": "no_payload_limit",
                        "payload_type": label,
                        "status": resp.status_code,
                        "detail": f"Server accepts large {label} payload without rejecting (HTTP {resp.status_code})",
                        "severity": "low",
                    })
                    raw_lines.append(f"  LOW: Accepts large {label} payload (HTTP {resp.status_code})")
                else:
                    raw_lines.append(f"  OK: Rejects large {label} payload (HTTP {resp.status_code})")
            except Exception:
                continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "41_rate_limiting.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Rate limit scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
