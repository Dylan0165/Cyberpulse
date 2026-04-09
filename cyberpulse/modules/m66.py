"""M66 — Third-Party Script & Supply Chain Risk Analysis."""
import requests
import re
from urllib.parse import urlparse

class Scanner:
    name = "Third-Party Script Analysis"
    phase = "scanning"
    description = "Analyze third-party script inclusions for supply chain attack risks."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 12)

        risky_cdns = [
            "unpkg.com", "jsdelivr.net", "cdnjs.cloudflare.com",
            "rawgit.com", "raw.githubusercontent.com", "gitcdn.xyz",
        ]

        analytics_trackers = [
            "google-analytics.com", "googletagmanager.com",
            "hotjar.com", "fullstory.com", "logrocket.com",
            "mixpanel.com", "segment.com", "intercom.io",
        ]

        try:
            r = requests.get(self.base, timeout=timeout, verify=False)
            content = r.text
            raw.append(f"Page loaded: {r.status_code}, {len(content)} bytes")
        except Exception as e:
            return {"findings": [{"type": "error", "detail": str(e), "severity": "info"}], "raw_output": str(e)}

        # Find all script src attributes
        script_urls = re.findall(r'<script[^>]+src=["\']([^"\']+)["\']', content, re.IGNORECASE)
        raw.append(f"Script tags found: {len(script_urls)}")

        external_scripts = []
        for url in script_urls:
            if url.startswith("//") or "://" in url:
                ext_domain = urlparse(url if "://" in url else "https:" + url).netloc
                if ext_domain and ext_domain != self.target.lstrip("www."):
                    external_scripts.append((url, ext_domain))

        # Check for risky CDNs
        for url, domain in external_scripts:
            for cdn in risky_cdns:
                if cdn in domain:
                    # Check for SRI
                    sri_match = re.search(
                        r'<script[^>]+src=["\']' + re.escape(url) + r'["\'][^>]*integrity=["\'][^"\']+["\']',
                        content,
                        re.IGNORECASE,
                    )
                    if not sri_match:
                        findings.append({
                            "type": "supply_chain",
                            "detail": f"Third-party script from {domain} without Subresource Integrity (SRI) — supply chain risk",
                            "severity": "medium",
                            "script_url": url,
                            "domain": domain,
                        })

        # Check for analytics/tracking
        found_trackers = set()
        for url, domain in external_scripts:
            for tracker in analytics_trackers:
                if tracker in domain and tracker not in found_trackers:
                    found_trackers.add(tracker)
                    findings.append({
                        "type": "tracking",
                        "detail": f"Third-party tracking/analytics loaded: {domain}",
                        "severity": "low",
                        "domain": domain,
                    })

        # Check inline scripts for dangerous patterns
        inline_scripts = re.findall(r'<script[^>]*>(.*?)</script>', content, re.DOTALL | re.IGNORECASE)
        dangerous_patterns = [
            (r'eval\s*\(', "eval() usage in inline script"),
            (r'document\.write\s*\(', "document.write() in inline script"),
            (r'innerHTML\s*=', "innerHTML assignment in inline script"),
            (r'localStorage\.setItem', "Data written to localStorage"),
        ]
        for script in inline_scripts:
            for pattern, desc in dangerous_patterns:
                if re.search(pattern, script):
                    findings.append({
                        "type": "dangerous_script",
                        "detail": f"Potentially dangerous pattern in inline script: {desc}",
                        "severity": "low",
                    })
                    break

        if external_scripts:
            findings.append({
                "type": "info",
                "detail": f"Total external scripts: {len(external_scripts)} from {len(set(d for _, d in external_scripts))} domains",
                "severity": "info",
            })

        if not any(f["severity"] in ("high", "critical", "medium") for f in findings):
            findings.append({"type": "info", "detail": "No critical third-party script risks identified", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
