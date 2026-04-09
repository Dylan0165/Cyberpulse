"""M54 — Deserialization Attack Detection."""
import requests
import base64

class Scanner:
    name = "Deserialization Testing"
    phase = "exploitation"
    description = "Detect insecure deserialization in Java, PHP, Python, and .NET applications."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 12)

        # Fingerprint the tech stack
        try:
            r = requests.get(self.base, timeout=timeout, verify=False)
            tech = []
            server = r.headers.get("Server", "")
            powered = r.headers.get("X-Powered-By", "")
            raw.append(f"Server: {server}, X-Powered-By: {powered}")

            if "java" in server.lower() or "tomcat" in server.lower() or "jboss" in server.lower():
                tech.append("java")
            if "php" in powered.lower():
                tech.append("php")
            if "asp.net" in powered.lower():
                tech.append("dotnet")
            if "python" in server.lower() or "django" in r.text.lower() or "flask" in r.text.lower():
                tech.append("python")
        except Exception as e:
            raw.append(f"Fingerprint error: {e}")
            tech = []

        # Java deserialization — look for serialized object markers
        java_cookie_paths = ["/manager", "/admin", "/console", "/struts", "/api/v1", "/remoting"]
        JAVA_SER_MAGIC = b"\xac\xed\x00\x05"
        for path in java_cookie_paths:
            try:
                rj = requests.get(self.base.rstrip("/") + path, timeout=timeout, verify=False)
                raw.append(f"Java probe {path}: {rj.status_code}")
                if rj.status_code == 200:
                    for cookie_val in rj.cookies.values():
                        try:
                            decoded = base64.b64decode(cookie_val + "==")
                            if decoded.startswith(JAVA_SER_MAGIC):
                                findings.append({
                                    "type": "deserialization",
                                    "detail": f"Java serialized object detected in cookie at {path}",
                                    "severity": "critical",
                                    "url": self.base + path,
                                    "technology": "java",
                                })
                        except Exception:
                            pass
            except Exception as e:
                raw.append(f"Java probe error: {e}")

        # PHP deserialization — look for serialized PHP in params
        php_payloads = [
            ("data", 'O:8:"stdClass":0:{}'),
            ("obj", 'a:1:{i:0;s:4:"test";}'),
        ]
        php_endpoints = ["/", "/index.php", "/api.php"]
        if "php" in tech:
            for ep in php_endpoints:
                for param, val in php_payloads:
                    try:
                        rp = requests.get(
                            self.base.rstrip("/") + ep,
                            params={param: val},
                            timeout=timeout,
                            verify=False,
                        )
                        raw.append(f"PHP deser {ep}?{param}: {rp.status_code}")
                        if "unserialize" in rp.text.lower() or "__destruct" in rp.text.lower():
                            findings.append({
                                "type": "deserialization",
                                "detail": f"PHP unserialization error exposed at {ep}",
                                "severity": "critical",
                                "url": self.base + ep,
                                "technology": "php",
                            })
                    except Exception as e:
                        raw.append(f"PHP probe error: {e}")

        # .NET ViewState check
        try:
            r_net = requests.get(self.base, timeout=timeout, verify=False)
            if "__VIEWSTATE" in r_net.text:
                findings.append({
                    "type": "deserialization",
                    "detail": "ASP.NET ViewState detected — if MAC validation is disabled, deserialization RCE is possible",
                    "severity": "medium",
                    "url": self.base,
                    "technology": "dotnet",
                })
                raw.append("ViewState detected")
                if "EnableViewStateMac" in r_net.text or "__VIEWSTATEMAC" not in r_net.text:
                    findings[-1]["severity"] = "high"
                    findings[-1]["detail"] += " (MAC may be disabled)"
        except Exception as e:
            raw.append(f".NET probe error: {e}")

        if not any(f["type"] == "deserialization" for f in findings):
            findings.append({"type": "info", "detail": "No insecure deserialization indicators detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
