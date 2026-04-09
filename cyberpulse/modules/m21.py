"""Module 21 — Firewall & WAF Detection.

Detects Web Application Firewalls (WAF) and firewall rules
by analyzing response behaviors to malicious-looking payloads.
"""

import json
import logging
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m21")

# Known WAF signatures in headers / response bodies
WAF_SIGNATURES = {
    "Cloudflare": ["cf-ray", "cloudflare", "__cfduid"],
    "AWS WAF": ["awselb", "x-amzn-requestid", "x-amz-cf-id"],
    "Akamai": ["akamai", "x-akamai-transformed", "akamai-ghost"],
    "Imperva / Incapsula": ["incap_ses", "visid_incap", "x-iinfo"],
    "Sucuri": ["sucuri", "x-sucuri-id", "x-sucuri-cache"],
    "F5 BIG-IP": ["bigipserver", "f5-bigip", "x-wa-info"],
    "Barracuda": ["barra_counter_session", "barracuda"],
    "Fortinet / FortiWeb": ["fortiwafsid", "fortiweb"],
    "ModSecurity": ["mod_security", "modsecurity"],
    "Wordfence": ["wordfence", "wf_loginhash"],
    "DenyAll": ["denyall", "sessioncookie"],
    "Citrix NetScaler": ["ns_af", "citrix_ns_id", "nsprotect"],
    "Radware": ["x-sl-compstate", "rdwr"],
    "Comodo": ["x-cwaf-ver"],
    "StackPath": ["x-sp-waf"],
}

# Payloads that trigger WAFs
WAF_TEST_PAYLOADS = [
    "/<script>alert(1)</script>",
    "/?id=1' OR '1'='1",
    "/?cmd=cat+/etc/passwd",
    "/?file=../../etc/passwd",
    "/?q=<img src=x onerror=alert(1)>",
    "/wp-admin/admin-ajax.php?action=test",
    "/?search={{7*7}}",
    "/../../../etc/shadow",
]


class Scanner:
    name = "Firewall & WAF Detection"
    phase = "reconnaissance"
    description = "Detects Web Application Firewalls and firewall configurations"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"WAF/Firewall detection for {self.target}"]

        base_url = self._get_base_url()

        # Phase 1: Header analysis
        raw_lines.append("\n[Phase 1: Response Header Analysis]")
        header_waf = self._detect_from_headers(base_url)
        if header_waf:
            for waf_name in header_waf:
                raw_lines.append(f"  WAF Detected via headers: {waf_name}")
                findings.append({
                    "type": "waf_detected",
                    "waf": waf_name,
                    "method": "header_analysis",
                    "detail": f"WAF '{waf_name}' detected through response headers",
                    "severity": "info",
                })
        else:
            raw_lines.append("  No WAF detected in response headers")

        # Phase 2: Behavioral analysis with payloads
        raw_lines.append("\n[Phase 2: Behavioral Analysis]")
        blocked_count = 0
        altered_count = 0

        normal_resp = self._safe_get(base_url)
        normal_status = normal_resp.status_code if normal_resp else 0
        normal_length = len(normal_resp.text) if normal_resp else 0

        for payload in WAF_TEST_PAYLOADS:
            url = base_url + payload
            resp = self._safe_get(url)
            if not resp:
                continue

            if resp.status_code in (403, 406, 429, 501, 503):
                blocked_count += 1
                raw_lines.append(f"  BLOCKED ({resp.status_code}): {payload[:50]}")
            elif resp.status_code == 200 and normal_length > 0:
                diff = abs(len(resp.text) - normal_length)
                if diff > normal_length * 0.5:
                    altered_count += 1
                    raw_lines.append(f"  ALTERED: {payload[:50]} (response size changed significantly)")

        if blocked_count >= 3:
            findings.append({
                "type": "waf_behavioral",
                "blocked_requests": blocked_count,
                "altered_requests": altered_count,
                "detail": f"WAF actively blocking malicious payloads ({blocked_count}/{len(WAF_TEST_PAYLOADS)} blocked)",
                "severity": "info",
            })
            raw_lines.append(f"\n  Result: WAF actively filtering ({blocked_count} blocked, {altered_count} altered)")
        elif blocked_count == 0 and altered_count == 0:
            findings.append({
                "type": "no_waf",
                "detail": "No WAF detected — target may be unprotected against web attacks",
                "severity": "medium",
            })
            raw_lines.append("\n  WARNING: No WAF detected — target appears unprotected")
        else:
            raw_lines.append(f"\n  Partial protection: {blocked_count} blocked, {altered_count} altered")

        # Phase 3: Check common WAF error pages
        raw_lines.append("\n[Phase 3: WAF Error Page Detection]")
        error_waf = self._check_error_pages(base_url)
        for waf in error_waf:
            raw_lines.append(f"  WAF error page detected: {waf}")
            findings.append({
                "type": "waf_error_page",
                "waf": waf,
                "detail": f"WAF '{waf}' revealed through error page",
                "severity": "low",
            })

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "21_waf_detection.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("WAF detection %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                resp = self.session.head(f"{scheme}://{self.target}", timeout=5)
                if resp.status_code < 500:
                    return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"

    def _safe_get(self, url: str):
        try:
            return self.session.get(url, timeout=10, allow_redirects=True)
        except Exception:
            return None

    def _detect_from_headers(self, base_url: str) -> list[str]:
        detected = []
        resp = self._safe_get(base_url)
        if not resp:
            return detected

        all_headers = " ".join(f"{k}: {v}" for k, v in resp.headers.items()).lower()
        cookies = " ".join(f"{k}={v}" for k, v in resp.cookies.items()).lower()
        combined = all_headers + " " + cookies

        for waf_name, signatures in WAF_SIGNATURES.items():
            for sig in signatures:
                if sig.lower() in combined:
                    detected.append(waf_name)
                    break
        return detected

    def _check_error_pages(self, base_url: str) -> list[str]:
        detected = []
        # Request a path that should 404
        resp = self._safe_get(base_url + "/cyberpulse-waf-test-nonexistent-page-12345")
        if not resp:
            return detected

        body = resp.text.lower()
        if "cloudflare" in body:
            detected.append("Cloudflare")
        if "incapsula" in body or "imperva" in body:
            detected.append("Imperva/Incapsula")
        if "sucuri" in body:
            detected.append("Sucuri")
        if "akamai" in body:
            detected.append("Akamai")
        if "ddos-guard" in body:
            detected.append("DDoS-Guard")
        if "wordfence" in body:
            detected.append("Wordfence")
        return detected
