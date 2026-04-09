"""M56 — Clickjacking & UI Redressing Detection."""
import requests

class Scanner:
    name = "Clickjacking & UI Redressing"
    phase = "scanning"
    description = "Detect missing X-Frame-Options / CSP frame-ancestors and UI redressing risks."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        sensitive_pages = [
            "/", "/login", "/admin", "/account", "/settings",
            "/payment", "/checkout", "/transfer", "/profile",
        ]

        for path in sensitive_pages:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False, allow_redirects=True)
                if r.status_code not in (200, 401, 403):
                    continue
                raw.append(f"{path}: {r.status_code}")

                xfo = r.headers.get("X-Frame-Options", "").upper()
                csp = r.headers.get("Content-Security-Policy", "")
                has_frame_ancestor = "frame-ancestors" in csp.lower()

                if not xfo and not has_frame_ancestor:
                    findings.append({
                        "type": "clickjacking",
                        "detail": f"No X-Frame-Options or CSP frame-ancestors on {path} — clickjacking possible",
                        "severity": "medium",
                        "url": url,
                        "x_frame_options": xfo or "missing",
                        "csp_frame_ancestors": "missing",
                    })
                elif xfo == "ALLOW-FROM":
                    findings.append({
                        "type": "clickjacking",
                        "detail": f"X-Frame-Options: ALLOW-FROM is deprecated and ignored by modern browsers",
                        "severity": "low",
                        "url": url,
                    })
                else:
                    raw.append(f"  Protected: XFO={xfo or 'n/a'}, frame-ancestors={'yes' if has_frame_ancestor else 'no'}")

                # Check for framing-related JS
                if "frameOptions" in r.text or "top.location" in r.text or "self.location" in r.text:
                    findings.append({
                        "type": "info",
                        "detail": f"JavaScript frame-busting detected at {path} — may be bypassable via sandbox iframe",
                        "severity": "low",
                        "url": url,
                    })
            except Exception as e:
                raw.append(f"{path}: {e}")

        if not any(f["type"] == "clickjacking" for f in findings):
            findings.append({"type": "info", "detail": "Clickjacking protection properly configured", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
