"""M59 — Content Security Policy Deep Analysis."""
import requests
import re

class Scanner:
    name = "CSP Deep Analysis"
    phase = "scanning"
    description = "Deeply analyze Content-Security-Policy headers for weaknesses and bypass vectors."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        unsafe_keywords = ["'unsafe-inline'", "'unsafe-eval'", "data:", "*", "http:"]
        deprecated_directives = ["reflected-xss", "referrer", "block-all-mixed-content"]

        try:
            r = requests.get(self.base, timeout=timeout, verify=False)
            csp = r.headers.get("Content-Security-Policy", "") or r.headers.get("Content-Security-Policy-Report-Only", "")
            raw.append(f"CSP: {csp[:300]}" if csp else "CSP: not present")
        except Exception as e:
            return {"findings": [{"type": "error", "detail": str(e), "severity": "info"}], "raw_output": str(e)}

        if not csp:
            findings.append({
                "type": "csp_missing",
                "detail": "Content-Security-Policy header is not set — XSS mitigation absent",
                "severity": "medium",
            })
            return {"findings": findings, "raw_output": "\n".join(raw)}

        # Parse directives
        directives = {}
        for part in csp.split(";"):
            part = part.strip()
            if part:
                tokens = part.split()
                if tokens:
                    directives[tokens[0].lower()] = tokens[1:]

        # Check for unsafe values
        for directive, values in directives.items():
            for val in values:
                if val.lower() in unsafe_keywords or val == "*":
                    severity = "high" if val in ("'unsafe-inline'", "'unsafe-eval'") else "medium"
                    findings.append({
                        "type": "csp_weak",
                        "detail": f"CSP directive '{directive}' contains unsafe value: {val}",
                        "severity": severity,
                        "directive": directive,
                        "value": val,
                    })

        # Check for missing important directives
        important = ["default-src", "script-src", "object-src", "base-uri"]
        for d in important:
            if d not in directives:
                findings.append({
                    "type": "csp_missing_directive",
                    "detail": f"CSP missing important directive: {d}",
                    "severity": "low",
                    "directive": d,
                })

        # Object-src none check (prevents Flash/plugins)
        obj_src = directives.get("object-src", [])
        if "'none'" not in obj_src and "object-src" not in directives:
            findings.append({
                "type": "csp_weak",
                "detail": "object-src not set to 'none' — plugins/Flash could execute malicious code",
                "severity": "medium",
            })

        # Nonce/hash vs unsafe-inline
        script_src = directives.get("script-src", []) or directives.get("default-src", [])
        has_nonce = any("nonce-" in v for v in script_src)
        has_hash = any("sha" in v for v in script_src)
        has_unsafe_inline = "'unsafe-inline'" in script_src
        if has_unsafe_inline and not (has_nonce or has_hash):
            findings.append({
                "type": "csp_weak",
                "detail": "script-src uses 'unsafe-inline' without nonce/hash — XSS bypass possible",
                "severity": "high",
            })

        # JSONP/CDN bypass check
        cdn_patterns = [r"cdn\.jsdelivr\.net", r"cdnjs\.cloudflare\.com", r"ajax\.googleapis\.com", r"unpkg\.com"]
        csp_str = " ".join(sum(directives.values(), []))
        for pattern in cdn_patterns:
            if re.search(pattern, csp_str, re.IGNORECASE):
                findings.append({
                    "type": "csp_bypass",
                    "detail": f"CSP allows CDN ({pattern}) which may host JSONP endpoints usable for bypass",
                    "severity": "medium",
                })

        # Deprecated directives
        for dep in deprecated_directives:
            if dep in directives:
                findings.append({
                    "type": "csp_deprecated",
                    "detail": f"Deprecated CSP directive used: {dep}",
                    "severity": "low",
                })

        if not any(f["severity"] in ("high", "medium") for f in findings):
            findings.append({"type": "info", "detail": "CSP appears reasonably configured", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
