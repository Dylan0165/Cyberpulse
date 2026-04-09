"""M61 — Certificate Transparency & TLS Certificate Analysis."""
import requests
import ssl
import socket
import datetime

class Scanner:
    name = "Certificate Transparency"
    phase = "reconnaissance"
    description = "Analyze CT logs, certificate details, and discover subdomains from transparency logs."

    def __init__(self, target, output_dir, config):
        self.target = target.split(":")[0]  # strip port
        self.output_dir = output_dir
        self.config = config
        self.base = f"https://{self.target}"

    def run(self):
        findings, raw = [], []
        timeout = self.config.get("timeout", 15)

        # Query crt.sh for certificate transparency logs
        try:
            r = requests.get(
                f"https://crt.sh/?q=%.{self.target}&output=json",
                timeout=timeout,
                verify=True,
            )
            if r.status_code == 200:
                certs = r.json()
                raw.append(f"CT log entries: {len(certs)}")

                # Collect unique subdomains
                subdomains = set()
                for cert in certs:
                    name = cert.get("name_value", "")
                    for n in name.split("\n"):
                        n = n.strip().lstrip("*.")
                        if n and n.endswith(self.target) and n != self.target:
                            subdomains.add(n)

                if subdomains:
                    findings.append({
                        "type": "ct_subdomains",
                        "detail": f"CT logs reveal {len(subdomains)} subdomains: {', '.join(sorted(subdomains)[:20])}",
                        "severity": "info",
                        "subdomains": sorted(subdomains),
                        "count": len(subdomains),
                    })

                # Wildcard certs
                wildcards = [c for c in certs if "*." in c.get("name_value", "")]
                if wildcards:
                    findings.append({
                        "type": "wildcard_cert",
                        "detail": f"Wildcard certificate(s) issued for {self.target} — all subdomains share the same cert",
                        "severity": "low",
                        "count": len(wildcards),
                    })

                # Old/expiring certificates
                now = datetime.datetime.utcnow()
                for cert in certs[:50]:
                    not_after = cert.get("not_after", "")
                    if not_after:
                        try:
                            exp = datetime.datetime.strptime(not_after, "%Y-%m-%dT%H:%M:%S")
                            if exp < now:
                                findings.append({
                                    "type": "expired_cert",
                                    "detail": f"Expired certificate found in CT logs (expired {not_after})",
                                    "severity": "medium",
                                    "expired_at": not_after,
                                })
                                break
                        except Exception:
                            pass
        except Exception as e:
            raw.append(f"crt.sh error: {e}")
            findings.append({"type": "info", "detail": f"CT log query failed: {e}", "severity": "info"})

        # Direct TLS certificate inspection
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with socket.create_connection((self.target, 443), timeout=10) as sock:
                with ctx.wrap_socket(sock, server_hostname=self.target) as ssock:
                    cert = ssock.getpeercert()
                    not_after_ts = cert.get("notAfter", "")
                    raw.append(f"TLS cert expires: {not_after_ts}")
                    if not_after_ts:
                        exp = ssl.cert_time_to_seconds(not_after_ts)
                        days_left = (exp - datetime.datetime.utcnow().timestamp()) / 86400
                        if days_left < 30:
                            findings.append({
                                "type": "cert_expiring",
                                "detail": f"TLS certificate expires in {int(days_left)} days",
                                "severity": "medium" if days_left > 7 else "high",
                                "days_remaining": int(days_left),
                            })

                    # Check SANs
                    sans = [v for t, v in cert.get("subjectAltName", []) if t == "DNS"]
                    raw.append(f"SANs: {', '.join(sans[:10])}")
                    if len(sans) > 50:
                        findings.append({
                            "type": "info",
                            "detail": f"Certificate covers {len(sans)} SANs — large attack surface",
                            "severity": "low",
                            "san_count": len(sans),
                        })
        except Exception as e:
            raw.append(f"TLS inspection error: {e}")

        if not findings:
            findings.append({"type": "info", "detail": "Certificate transparency analysis complete — no issues found", "severity": "info"})

        return {"findings": findings, "raw_output": "\n".join(raw)}
