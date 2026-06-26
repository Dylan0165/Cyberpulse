"""Enrich findings with OWASP Top 10 / CWE / MITRE ATT&CK references + CVE links."""

from __future__ import annotations

import re

OWASP_MAPPING = {
    "sqli":            {"owasp": "A03:2021", "label": "Injection",                 "cwe": "CWE-89"},
    "xss":             {"owasp": "A03:2021", "label": "Injection",                 "cwe": "CWE-79"},
    "xxe":             {"owasp": "A05:2021", "label": "Security Misconfiguration", "cwe": "CWE-611"},
    "idor":            {"owasp": "A01:2021", "label": "Broken Access Control",     "cwe": "CWE-639"},
    "csrf":            {"owasp": "A01:2021", "label": "Broken Access Control",     "cwe": "CWE-352"},
    "ssrf":            {"owasp": "A10:2021", "label": "SSRF",                      "cwe": "CWE-918"},
    "lfi":             {"owasp": "A01:2021", "label": "Broken Access Control",     "cwe": "CWE-22"},
    "rce":             {"owasp": "A03:2021", "label": "Injection",                 "cwe": "CWE-77"},
    "open_redirect":   {"owasp": "A01:2021", "label": "Broken Access Control",     "cwe": "CWE-601"},
    "ssl_weak":        {"owasp": "A02:2021", "label": "Crypto Failures",           "cwe": "CWE-326"},
    "ssl_expired":     {"owasp": "A02:2021", "label": "Crypto Failures",           "cwe": "CWE-295"},
    "default_creds":   {"owasp": "A07:2021", "label": "Auth Failures",             "cwe": "CWE-521"},
    "brute_force":     {"owasp": "A07:2021", "label": "Auth Failures",             "cwe": "CWE-307"},
    "info_disclosure": {"owasp": "A05:2021", "label": "Security Misconfiguration", "cwe": "CWE-200"},
    "cve":             {"owasp": "A06:2021", "label": "Vulnerable Components",     "cwe": "CWE-1035"},
    "secrets":         {"owasp": "A02:2021", "label": "Crypto Failures",           "cwe": "CWE-312"},
    "cors":            {"owasp": "A05:2021", "label": "Security Misconfiguration", "cwe": "CWE-942"},
    "rate_limit":      {"owasp": "A04:2021", "label": "Insecure Design",           "cwe": "CWE-770"},
}

MITRE_MAPPING = {
    "sqli": "T1190", "xss": "T1059.007", "rce": "T1190", "brute_force": "T1110",
    "default_creds": "T1078", "cve": "T1190", "secrets": "T1552", "ssrf": "T1090",
}

_DEFAULT = {"owasp": "A05:2021", "label": "Security Misconfiguration", "cwe": "CWE-200"}
_CVE_RE = re.compile(r"CVE-\d{4}-\d+", re.IGNORECASE)


class FindingMapper:
    @staticmethod
    def enrich(finding: dict) -> dict:
        """Add owasp_category/label, cwe(+url), mitre_technique, and CVE link."""
        if not isinstance(finding, dict):
            return finding
        ftype = str(finding.get("type", "")).lower()
        mapping = OWASP_MAPPING.get(ftype, _DEFAULT)
        finding["owasp_category"] = mapping["owasp"]
        finding["owasp_label"] = mapping["label"]
        finding["cwe"] = mapping["cwe"]
        finding["cwe_url"] = f"https://cwe.mitre.org/data/definitions/{mapping['cwe'].replace('CWE-','')}.html"
        finding["mitre_technique"] = MITRE_MAPPING.get(ftype, "")

        cve_match = _CVE_RE.search(str(finding.get("description", "")))
        if cve_match:
            cve_id = cve_match.group().upper()
            finding["cve_id"] = cve_id
            finding["cve_url"] = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        return finding

    @staticmethod
    def owasp_coverage(findings: list[dict]) -> list[dict]:
        """Summarise findings per OWASP category for the report coverage table."""
        buckets: dict[str, dict] = {}
        for f in findings or []:
            cat = f.get("owasp_category") or _DEFAULT["owasp"]
            label = f.get("owasp_label") or _DEFAULT["label"]
            b = buckets.setdefault(cat, {"owasp": cat, "label": label, "count": 0, "worst": "INFO"})
            b["count"] += 1
            order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
            sev = str(f.get("severity", "INFO")).upper()
            if sev in order and order.index(sev) < order.index(b["worst"]):
                b["worst"] = sev
        return sorted(buckets.values(), key=lambda x: x["owasp"])
