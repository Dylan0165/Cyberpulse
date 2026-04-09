"""M51 — HTTP Request Smuggling & Desync Detection."""
import requests
import time

class Scanner:
    name = "HTTP Request Smuggling"
    phase = "exploitation"
    description = "Detect CL.TE and TE.CL request smuggling vulnerabilities."

    def __init__(self, target, output_dir, config):
        self.target = target
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{target}" if not target.startswith("http") else target

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # Test 1: CL.TE smuggling probe
        try:
            payload = (
                "POST / HTTP/1.1\r\n"
                f"Host: {self.target}\r\n"
                "Content-Length: 6\r\n"
                "Transfer-Encoding: chunked\r\n\r\n"
                "0\r\n\r\nX"
            )
            headers = {
                "Content-Length": "6",
                "Transfer-Encoding": "chunked",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            r = requests.post(self.base, headers=headers, data="0\r\n\r\nX", timeout=timeout, verify=False)
            raw.append(f"CL.TE probe: {r.status_code}")
            if r.status_code in (400, 408, 505):
                findings.append({
                    "type": "http_smuggling",
                    "detail": f"Possible CL.TE smuggling indicator: HTTP {r.status_code}",
                    "severity": "high",
                    "url": self.base,
                })
        except Exception as e:
            raw.append(f"CL.TE probe error: {e}")

        # Test 2: TE.CL probe
        try:
            headers2 = {
                "Transfer-Encoding": "chunked",
                "Content-Length": "4",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            t0 = time.time()
            r2 = requests.post(self.base + "/", headers=headers2, data="1\r\nZ\r\n0\r\n\r\n", timeout=timeout, verify=False)
            elapsed = time.time() - t0
            raw.append(f"TE.CL probe: {r2.status_code} ({elapsed:.2f}s)")
            if elapsed > 5:
                findings.append({
                    "type": "http_smuggling",
                    "detail": f"TE.CL timing anomaly: {elapsed:.1f}s delay after chunked request",
                    "severity": "high",
                    "url": self.base,
                })
        except Exception as e:
            raw.append(f"TE.CL probe error: {e}")

        # Test 3: Obfuscated TE header
        try:
            headers3 = {
                "Transfer-Encoding": "xchunked",
                "Content-Length": "5",
                "Content-Type": "application/x-www-form-urlencoded",
            }
            r3 = requests.post(self.base, headers=headers3, data="hello", timeout=timeout, verify=False)
            raw.append(f"TE obfuscation probe: {r3.status_code}")
            if r3.status_code == 200:
                findings.append({
                    "type": "http_smuggling",
                    "detail": "Server accepted obfuscated Transfer-Encoding header (xchunked) — potential desync risk",
                    "severity": "medium",
                    "url": self.base,
                })
        except Exception as e:
            raw.append(f"TE obfuscation probe error: {e}")

        if not findings:
            findings.append({"type": "info", "detail": "No HTTP request smuggling indicators detected", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
