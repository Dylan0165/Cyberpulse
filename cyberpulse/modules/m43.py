"""Module 43 — Business Logic Vulnerability Testing.

Tests for flaws in business workflows: price manipulation, coupon abuse,
order flow bypass, race conditions, and functional logic errors.
"""

import json
import logging
import re
import threading
import time
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m43")


class Scanner:
    name = "Business Logic Vulnerabilities"
    phase = "exploitation"
    description = "Tests for business logic flaws: price manipulation, race conditions, flow bypass"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Business logic vulnerability testing for {self.target}"]
        base_url = self._get_base_url()

        # Phase 1: Price / quantity manipulation
        raw_lines.append("\n[Phase 1: Price & Quantity Manipulation]")
        ecommerce_endpoints = [
            "/api/cart/add", "/api/cart", "/api/order",
            "/cart/add", "/checkout", "/api/checkout",
            "/api/products/buy", "/api/purchase",
        ]
        manipulations = [
            {"price": 0, "quantity": 1},
            {"price": -1, "quantity": 1},
            {"price": 0.01, "quantity": 1},
            {"quantity": -1, "price": 100},
            {"quantity": 999999, "price": 100},
            {"amount": 0},
            {"total": 0},
            {"discount": 100},
        ]
        for endpoint in ecommerce_endpoints:
            for payload in manipulations:
                url = base_url + endpoint
                try:
                    resp = self.session.post(url, json=payload, timeout=8)
                    if resp.status_code in (200, 201):
                        try:
                            data = resp.json()
                            if data.get("success") or data.get("order_id") or data.get("cart"):
                                findings.append({
                                    "type": "price_manipulation",
                                    "endpoint": endpoint,
                                    "payload": payload,
                                    "detail": f"Price/quantity manipulation accepted at {endpoint}: {payload}",
                                    "severity": "high",
                                })
                                raw_lines.append(f"  HIGH: {endpoint} accepts {payload}")
                                break
                        except Exception:
                            pass
                except Exception:
                    continue

        # Phase 2: Coupon / discount abuse
        raw_lines.append("\n[Phase 2: Coupon & Discount Abuse]")
        coupon_endpoints = ["/api/coupon", "/api/discount", "/api/promo",
                            "/api/cart/coupon", "/api/apply-coupon"]
        abuse_tests = [
            {"code": "TEST", "times": 3},  # Reuse same code
            {"code": "DISCOUNT100"},
            {"code": "FREE"},
            {"code": "' OR '1'='1"},
            {"code": "ADMIN"},
        ]
        for endpoint in coupon_endpoints:
            for test in abuse_tests:
                url = base_url + endpoint
                code = test.get("code", "TEST")
                times = test.get("times", 1)
                for _ in range(times):
                    try:
                        resp = self.session.post(url, json={"code": code}, timeout=8)
                        if resp.status_code == 200:
                            try:
                                data = resp.json()
                                if data.get("discount") or data.get("applied") or data.get("success"):
                                    findings.append({
                                        "type": "coupon_abuse",
                                        "endpoint": endpoint,
                                        "code": code,
                                        "detail": f"Coupon accepted at {endpoint}: '{code}'",
                                        "severity": "medium",
                                    })
                                    raw_lines.append(f"  MEDIUM: Coupon '{code}' accepted at {endpoint}")
                                    break
                            except Exception:
                                pass
                    except Exception:
                        continue

        # Phase 3: Race condition testing
        raw_lines.append("\n[Phase 3: Race Condition Detection]")
        race_endpoints = [
            "/api/transfer", "/api/withdraw", "/api/redeem",
            "/api/vote", "/api/like", "/api/claim",
        ]
        for endpoint in race_endpoints:
            url = base_url + endpoint
            results = []

            def send_request():
                try:
                    s = requests.Session()
                    s.verify = False
                    r = s.post(url, json={"amount": 1}, timeout=8)
                    results.append(r.status_code)
                except Exception:
                    pass

            # Send concurrent requests
            threads = []
            for _ in range(5):
                t = threading.Thread(target=send_request)
                threads.append(t)
                t.start()
            for t in threads:
                t.join(timeout=10)

            success_count = sum(1 for s in results if s in (200, 201))
            if success_count > 1:
                findings.append({
                    "type": "race_condition",
                    "endpoint": endpoint,
                    "successful_requests": success_count,
                    "detail": f"Race condition at {endpoint}: {success_count}/{len(results)} requests succeeded simultaneously",
                    "severity": "high",
                })
                raw_lines.append(f"  HIGH: Race condition at {endpoint} ({success_count} simultaneous successes)")

        # Phase 4: Workflow bypass (skip steps)
        raw_lines.append("\n[Phase 4: Workflow Step Bypass]")
        # Try to access step 3 (e.g., payment confirmation) without doing steps 1-2
        step_sequences = [
            ["/checkout/step3", "/checkout/complete", "/order/confirm"],
            ["/register/verify", "/register/complete"],
            ["/payment/success", "/order/success"],
        ]
        for steps in step_sequences:
            for step in steps:
                url = base_url + step
                try:
                    resp = self.session.get(url, timeout=8, allow_redirects=False)
                    if resp.status_code == 200:
                        findings.append({
                            "type": "workflow_bypass",
                            "path": step,
                            "detail": f"Workflow step accessible without prerequisites: {step}",
                            "severity": "medium",
                        })
                        raw_lines.append(f"  MEDIUM: Workflow bypass at {step}")
                except Exception:
                    continue

        # Phase 5: Negative value / integer overflow testing
        raw_lines.append("\n[Phase 5: Numeric Boundary Testing]")
        numeric_endpoints = [
            "/api/transfer", "/api/balance", "/api/withdraw",
            "/api/points", "/api/credits",
        ]
        boundary_values = [
            -1, -100, 0, 2147483647, 2147483648,
            9999999999, 0.001, -0.001,
        ]
        for endpoint in numeric_endpoints:
            for value in boundary_values:
                url = base_url + endpoint
                try:
                    resp = self.session.post(url, json={"amount": value}, timeout=8)
                    if resp.status_code in (200, 201):
                        try:
                            data = resp.json()
                            if data.get("success") or data.get("balance") is not None:
                                findings.append({
                                    "type": "numeric_boundary",
                                    "endpoint": endpoint,
                                    "value": value,
                                    "detail": f"Boundary value {value} accepted at {endpoint}",
                                    "severity": "medium",
                                })
                                raw_lines.append(f"  MEDIUM: {endpoint} accepts value={value}")
                                break
                        except Exception:
                            pass
                except Exception:
                    continue

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "43_business_logic.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Business logic scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
