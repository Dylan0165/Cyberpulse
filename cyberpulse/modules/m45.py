"""Module 45 — Subdomain Takeover Detection.

Identifies dangling DNS records and unclaimed cloud resources that
could allow subdomain takeover attacks.
"""

import json
import logging
import re
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m45")

# CNAME targets known to be vulnerable to takeover if unclaimed
TAKEOVER_FINGERPRINTS = {
    # Service: (CNAME pattern, error string in page)
    "github": ("github.io", "There isn't a GitHub Pages site here"),
    "heroku": ("herokuapp.com", "No such app"),
    "aws_s3": ("s3.amazonaws.com", "NoSuchBucket"),
    "aws_eb": ("elasticbeanstalk.com", "NXDOMAIN"),
    "azure": ("azurewebsites.net", "404 Web Site not found"),
    "azure_blob": ("blob.core.windows.net", "BlobNotFound"),
    "shopify": ("myshopify.com", "Sorry, this shop is currently unavailable"),
    "tumblr": ("tumblr.com", "There's nothing here"),
    "wordpress": ("wordpress.com", "Do you want to register"),
    "pantheon": ("pantheonsite.io", "404 error unknown site"),
    "zendesk": ("zendesk.com", "Help Center Closed"),
    "teamwork": ("teamwork.com", "Oops - We didn't find your site"),
    "helpjuice": ("helpjuice.com", "We could not find what you're looking for"),
    "helpscout": ("helpscoutdocs.com", "No settings were found"),
    "ghost": ("ghost.io", "The thing you were looking for is no longer here"),
    "surge": ("surge.sh", "project not found"),
    "bitbucket": ("bitbucket.io", "Repository not found"),
    "netlify": ("netlify.app", "Not Found"),
    "fly": ("fly.dev", "404 Not Found"),
    "vercel": ("vercel.app", "NOT_FOUND"),
    "render": ("onrender.com", "not found"),
    "cargo": ("cargocollective.com", "404 Not Found"),
    "ngrok": ("ngrok.io", "Tunnel .* not found"),
}


class Scanner:
    name = "Subdomain Takeover Detection"
    phase = "scanning"
    description = "Detects dangling DNS records vulnerable to subdomain takeover"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Subdomain takeover detection for {self.target}"]

        # Phase 1: Enumerate subdomains
        raw_lines.append("\n[Phase 1: Subdomain Enumeration]")
        subdomains = self._enumerate_subdomains()
        raw_lines.append(f"  Found {len(subdomains)} subdomains to test")

        # Phase 2: Check each subdomain for CNAME and takeover vulnerability
        raw_lines.append("\n[Phase 2: CNAME & Takeover Analysis]")
        for subdomain in subdomains:
            fqdn = f"{subdomain}.{self.target}"
            cname = self._get_cname(fqdn)

            if cname:
                raw_lines.append(f"  {fqdn} → CNAME → {cname}")

                # Check against takeover fingerprints
                for service, (pattern, error_str) in TAKEOVER_FINGERPRINTS.items():
                    if pattern in cname.lower():
                        # Verify: try to access and check for error page
                        vulnerable = self._check_takeover(fqdn, error_str)
                        if vulnerable:
                            findings.append({
                                "type": "subdomain_takeover",
                                "subdomain": fqdn,
                                "cname": cname,
                                "service": service,
                                "detail": f"TAKEOVER POSSIBLE: {fqdn} → {cname} ({service})",
                                "severity": "critical",
                            })
                            raw_lines.append(f"  CRITICAL: {fqdn} → {service} — TAKEOVER POSSIBLE!")
                        else:
                            raw_lines.append(f"  INFO: {fqdn} → {service} (claimed)")
                        break
            else:
                # Check for NXDOMAIN (dangling A record)
                try:
                    socket.gethostbyname(fqdn)
                except socket.gaierror:
                    # NXDOMAIN — could be a dangling record
                    findings.append({
                        "type": "dangling_dns",
                        "subdomain": fqdn,
                        "detail": f"Dangling DNS: {fqdn} has no resolution",
                        "severity": "low",
                    })
                    raw_lines.append(f"  LOW: Dangling DNS record {fqdn}")

        # Phase 3: Check main domain cloud provider headers
        raw_lines.append("\n[Phase 3: Cloud Provider Detection]")
        base_url = self._get_base_url()
        try:
            resp = self.session.get(base_url, timeout=10)
            headers = dict(resp.headers)
            cloud_indicators = {
                "x-amz-": "AWS",
                "x-azure-": "Azure",
                "x-goog-": "Google Cloud",
                "x-vercel-": "Vercel",
                "x-netlify": "Netlify",
                "cf-ray": "Cloudflare",
                "x-served-by": "Fastly/CDN",
            }
            for header_prefix, provider in cloud_indicators.items():
                for h in headers:
                    if h.lower().startswith(header_prefix):
                        findings.append({
                            "type": "cloud_provider",
                            "provider": provider,
                            "header": h,
                            "detail": f"Cloud provider detected: {provider} (via {h} header)",
                            "severity": "info",
                        })
                        raw_lines.append(f"  INFO: {provider} detected ({h})")
                        break
        except Exception:
            pass

        # Phase 4: NS record analysis
        raw_lines.append("\n[Phase 4: NS Record Analysis]")
        import subprocess
        try:
            result = subprocess.run(
                ["nslookup", "-type=NS", self.target],
                capture_output=True, text=True, timeout=10,
            )
            ns_servers = re.findall(r"nameserver\s*=\s*(\S+)", result.stdout)
            for ns in ns_servers:
                raw_lines.append(f"  NS: {ns}")
                # Check if NS is a third-party that might be reclaimable
                third_party_ns = ["cloudflare", "awsdns", "azure-dns", "googledomains",
                                  "dnsimple", "route53", "godaddy"]
                for tp in third_party_ns:
                    if tp in ns.lower():
                        findings.append({
                            "type": "ns_provider",
                            "nameserver": ns,
                            "provider": tp,
                            "detail": f"DNS hosted by {tp}: {ns}",
                            "severity": "info",
                        })
        except Exception:
            raw_lines.append("  NS lookup failed")

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "45_subdomain_takeover.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("Subdomain takeover scan %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _enumerate_subdomains(self) -> list[str]:
        """Enumerate common subdomains via DNS resolution."""
        wordlist = [
            "www", "mail", "ftp", "admin", "webmail", "smtp", "pop",
            "ns1", "ns2", "dns", "mx", "imap", "test", "dev",
            "staging", "api", "portal", "blog", "shop", "store",
            "cdn", "static", "assets", "media", "img", "images",
            "vpn", "remote", "gateway", "proxy", "git", "gitlab",
            "jenkins", "ci", "cd", "app", "web", "mobile",
            "intranet", "internal", "extranet", "beta", "alpha",
            "demo", "docs", "wiki", "help", "support", "status",
            "monitor", "grafana", "kibana", "elastic", "redis",
            "db", "database", "mysql", "postgres", "mongo",
            "auth", "sso", "login", "id", "oauth",
            "chat", "slack", "teams", "meet",
            "aws", "azure", "gcp", "cloud",
            "backup", "old", "new", "v2", "legacy",
        ]
        found = []
        for sub in wordlist:
            fqdn = f"{sub}.{self.target}"
            try:
                socket.gethostbyname(fqdn)
                found.append(sub)
            except socket.gaierror:
                continue
        return found

    def _get_cname(self, fqdn: str) -> str | None:
        """Resolve CNAME record for a FQDN."""
        import subprocess
        try:
            result = subprocess.run(
                ["nslookup", "-type=CNAME", fqdn],
                capture_output=True, text=True, timeout=5,
            )
            cnames = re.findall(r"canonical name\s*=\s*(\S+)", result.stdout)
            return cnames[0].rstrip(".") if cnames else None
        except Exception:
            return None

    def _check_takeover(self, fqdn: str, error_str: str) -> bool:
        """Check if accessing the subdomain shows an unclaimed service page."""
        for scheme in ("https", "http"):
            try:
                resp = self.session.get(f"{scheme}://{fqdn}", timeout=10,
                                        headers={"Host": fqdn})
                if re.search(error_str, resp.text, re.I):
                    return True
            except Exception:
                continue
        return False

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
