"""M65 — Serverless & Cloud Function Endpoint Discovery."""
import requests

class Scanner:
    name = "Serverless Functions Discovery"
    phase = "reconnaissance"
    description = "Discover exposed serverless functions, Lambda APIs, Azure Functions, and GCP Cloud Functions."

    def __init__(self, target, output_dir, config):
        self.target = target.split(":")[0]
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{self.target}"

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 10)

        # AWS API Gateway patterns
        aws_patterns = [
            "execute-api.amazonaws.com",
            ".lambda-url.",
            "amazonaws.com",
        ]

        # Common serverless path patterns
        serverless_paths = [
            "/.netlify/functions/",
            "/api/",
            "/functions/",
            "/.functions/",
            "/lambda/",
            "/_api/",
            "/fns/",
            "/.well-known/serverless",
            "/api/graphql",
            "/api/rest",
        ]

        # Known function names
        function_names = [
            "hello", "getUserInfo", "getUser", "createUser", "auth",
            "login", "signup", "sendEmail", "webhook", "payment",
            "process", "upload", "download", "search", "verify",
        ]

        for path in serverless_paths:
            url = self.base.rstrip("/") + path
            try:
                r = requests.get(url, timeout=timeout, verify=False)
                raw.append(f"{path}: {r.status_code}")
                if r.status_code in (200, 403, 404):
                    if "function" in r.text.lower() or "lambda" in r.text.lower() or r.status_code == 200:
                        findings.append({
                            "type": "serverless_endpoint",
                            "detail": f"Potential serverless function endpoint at {path} (HTTP {r.status_code})",
                            "severity": "low",
                            "url": url,
                        })
            except Exception as e:
                raw.append(f"{path}: {e}")

        # Probe individual function names
        for path in ["/.netlify/functions/", "/api/", "/functions/"]:
            for fn in function_names:
                url = self.base.rstrip("/") + path + fn
                try:
                    r = requests.get(url, timeout=timeout, verify=False)
                    if r.status_code in (200, 405):
                        raw.append(f"Function {fn}: {r.status_code}")
                        findings.append({
                            "type": "serverless_function",
                            "detail": f"Active serverless function discovered: {path}{fn}",
                            "severity": "medium",
                            "url": url,
                            "function_name": fn,
                        })
                except Exception:
                    pass

        # Check response headers for cloud provider signatures
        try:
            r = requests.get(self.base, timeout=timeout, verify=False)
            headers_str = str(r.headers).lower()
            raw.append(f"Checking headers for cloud signatures")

            cloud_signatures = {
                "x-amzn-requestid": ("AWS Lambda/API Gateway", "medium"),
                "x-amz-cf-id": ("AWS CloudFront", "info"),
                "x-azure-ref": ("Azure", "info"),
                "x-google-backends": ("Google Cloud", "info"),
                "cf-ray": ("Cloudflare Workers", "info"),
                "x-vercel-id": ("Vercel Serverless", "info"),
                "x-netlify-cache": ("Netlify Functions", "info"),
            }

            for header, (provider, severity) in cloud_signatures.items():
                if header in headers_str:
                    findings.append({
                        "type": "cloud_provider",
                        "detail": f"Cloud provider detected via headers: {provider}",
                        "severity": severity,
                        "provider": provider,
                        "header": header,
                    })
        except Exception as e:
            raw.append(f"Header check: {e}")

        if not any(f["type"] in ("serverless_function", "serverless_endpoint") and f["severity"] != "info" for f in findings):
            findings.append({"type": "info", "detail": "No exploitable serverless endpoints discovered", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
