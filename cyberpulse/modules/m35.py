"""Module 35 — Active Directory Reconnaissance.

Enumerates publicly-exposed Active Directory services, LDAP endpoints,
and Windows-specific configurations accessible via HTTP/S.
"""

import json
import logging
import socket
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m35")

AD_PORTS = [
    (88, "Kerberos"),
    (389, "LDAP"),
    (636, "LDAPS"),
    (445, "SMB"),
    (135, "RPC"),
    (3268, "Global Catalog"),
    (3269, "Global Catalog SSL"),
    (5985, "WinRM HTTP"),
    (5986, "WinRM HTTPS"),
    (9389, "AD Web Services"),
]

EXCHANGE_PATHS = [
    "/owa", "/ecp", "/autodiscover/autodiscover.xml",
    "/Microsoft-Server-ActiveSync", "/EWS/Exchange.asmx",
    "/OAB", "/rpc", "/mapi",
]

ADFS_PATHS = [
    "/adfs/ls", "/adfs/services/trust/mex",
    "/FederationMetadata/2007-06/FederationMetadata.xml",
]

SHAREPOINT_PATHS = [
    "/_layouts/viewlsts.aspx", "/_api/web",
    "/_vti_bin/shtml.dll", "/_catalogs/masterpage",
]


class Scanner:
    name = "Active Directory Reconnaissance"
    phase = "exploitation"
    description = "Enumerates exposed Active Directory and Windows services"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"Active Directory reconnaissance for {self.target}"]

        # Phase 1: AD-specific port scan
        raw_lines.append("\n[Phase 1: AD Port Scan]")
        try:
            ip = socket.gethostbyname(self.target)
            for port, service in AD_PORTS:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((ip, port))
                if result == 0:
                    findings.append({
                        "type": "ad_port",
                        "port": port,
                        "service": service,
                        "detail": f"AD service exposed: {service} on port {port}",
                        "severity": "high" if port in (389, 445, 88) else "medium",
                    })
                    raw_lines.append(f"  {'HIGH' if port in (389, 445, 88) else 'MEDIUM'}: {service} port {port} OPEN")
                sock.close()
        except Exception as e:
            raw_lines.append(f"  Port scan error: {e}")

        base_url = self._get_base_url()

        # Phase 2: Exchange Server detection
        raw_lines.append("\n[Phase 2: Exchange Server Detection]")
        for path in EXCHANGE_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 301, 302, 401, 403):
                    findings.append({
                        "type": "exchange",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"Exchange endpoint found: {path} (HTTP {resp.status_code})",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: Exchange {path} — HTTP {resp.status_code}")
            except Exception:
                continue

        # Phase 3: ADFS detection
        raw_lines.append("\n[Phase 3: ADFS Detection]")
        for path in ADFS_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 301, 302):
                    findings.append({
                        "type": "adfs",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"ADFS endpoint: {path} — may leak domain info",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: ADFS {path} — HTTP {resp.status_code}")
                    # Check for domain info in federation metadata
                    if "FederationMetadata" in path and resp.status_code == 200:
                        if "entityID" in resp.text:
                            findings.append({
                                "type": "adfs_domain_leak",
                                "detail": "ADFS metadata exposes entityID / domain name",
                                "severity": "medium",
                            })
                            raw_lines.append("  MEDIUM: ADFS metadata exposes domain info")
            except Exception:
                continue

        # Phase 4: SharePoint detection
        raw_lines.append("\n[Phase 4: SharePoint Detection]")
        for path in SHAREPOINT_PATHS:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                if resp.status_code in (200, 401, 403):
                    findings.append({
                        "type": "sharepoint",
                        "path": path,
                        "status": resp.status_code,
                        "detail": f"SharePoint endpoint: {path}",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: SharePoint {path} — HTTP {resp.status_code}")
            except Exception:
                continue

        # Phase 5: NTLM authentication endpoints
        raw_lines.append("\n[Phase 5: NTLM Auth Detection]")
        ntlm_paths = ["/", "/owa/", "/ecp/", "/autodiscover/", "/rpc/"]
        for path in ntlm_paths:
            url = base_url + path
            try:
                resp = self.session.get(url, timeout=8, allow_redirects=False)
                www_auth = resp.headers.get("WWW-Authenticate", "")
                if "NTLM" in www_auth or "Negotiate" in www_auth:
                    findings.append({
                        "type": "ntlm_auth",
                        "path": path,
                        "auth_header": www_auth[:200],
                        "detail": f"NTLM/Negotiate auth at {path} — may leak domain name",
                        "severity": "medium",
                    })
                    raw_lines.append(f"  MEDIUM: NTLM auth at {path}")
            except Exception:
                continue

        # Phase 6: Windows-specific headers
        raw_lines.append("\n[Phase 6: Windows-specific Headers]")
        try:
            resp = self.session.get(base_url, timeout=10)
            server = resp.headers.get("Server", "")
            powered = resp.headers.get("X-Powered-By", "")
            aspnet = resp.headers.get("X-AspNet-Version", "")

            if "IIS" in server:
                findings.append({
                    "type": "iis_detected",
                    "server": server,
                    "detail": f"IIS detected: {server}",
                    "severity": "info",
                })
                raw_lines.append(f"  INFO: IIS detected: {server}")

            if "ASP.NET" in powered or aspnet:
                findings.append({
                    "type": "aspnet_detected",
                    "version": aspnet or powered,
                    "detail": f"ASP.NET detected: {aspnet or powered}",
                    "severity": "info",
                })
                raw_lines.append(f"  INFO: ASP.NET: {aspnet or powered}")
        except Exception:
            pass

        raw_output = "\n".join(raw_lines)
        outfile = self.output_dir / "35_ad_recon.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings}, f, indent=2)

        logger.info("AD recon %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _get_base_url(self) -> str:
        for scheme in ("https", "http"):
            try:
                self.session.head(f"{scheme}://{self.target}", timeout=5)
                return f"{scheme}://{self.target}"
            except Exception:
                continue
        return f"http://{self.target}"
