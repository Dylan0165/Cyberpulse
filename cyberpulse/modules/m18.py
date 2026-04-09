"""Module 18 — CMS-Specific Vulnerability Checks.

Detects CMS type and tests for known CMS-specific vulnerabilities:
WordPress, Joomla, Drupal, Magento.
"""

import json
import logging
import re
from pathlib import Path

import requests

logger = logging.getLogger("cyberpulse.modules.m18")


class Scanner:
    name = "CMS Vulnerability Check"
    phase = "exploitation"
    description = "Tests for CMS-specific vulnerabilities (WordPress, Joomla, Drupal)"

    def __init__(self, target: str, output_dir: Path, config: dict):
        self.target = target
        self.output_dir = Path(output_dir)
        self.config = config
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "Mozilla/5.0 CyberPulse/1.0"
        self.session.verify = False

    def run(self) -> dict:
        findings = []
        raw_lines = [f"CMS vulnerability check for {self.target}"]

        base_url = f"https://{self.target}"
        try:
            self.session.head(base_url, timeout=5)
        except Exception:
            base_url = f"http://{self.target}"

        # Detect CMS
        cms = self._detect_cms(base_url)
        raw_lines.append(f"Detected CMS: {cms or 'none'}")

        if cms == "wordpress":
            wp_findings = self._check_wordpress(base_url)
            findings.extend(wp_findings)
            for f in wp_findings:
                raw_lines.append(f"  [{f['severity'].upper()}] {f.get('detail', f.get('type', ''))}")
        elif cms == "joomla":
            joomla_findings = self._check_joomla(base_url)
            findings.extend(joomla_findings)
            for f in joomla_findings:
                raw_lines.append(f"  [{f['severity'].upper()}] {f.get('detail', f.get('type', ''))}")
        elif cms == "drupal":
            drupal_findings = self._check_drupal(base_url)
            findings.extend(drupal_findings)
            for f in drupal_findings:
                raw_lines.append(f"  [{f['severity'].upper()}] {f.get('detail', f.get('type', ''))}")
        else:
            raw_lines.append("No known CMS detected — skipping CMS-specific checks")

        raw_output = "\n".join(raw_lines)

        outfile = self.output_dir / "18_cms.json"
        with open(outfile, "w", encoding="utf-8") as f:
            json.dump({"findings": findings, "cms": cms}, f, indent=2)

        logger.info("CMS check %s: %d findings", self.target, len(findings))
        return {"findings": findings, "raw_output": raw_output}

    def _detect_cms(self, base_url: str) -> str | None:
        try:
            resp = self.session.get(base_url, timeout=10)
            html = resp.text.lower()
            if "wp-content" in html or "wp-includes" in html:
                return "wordpress"
            if "/media/jui/" in html or "joomla" in html:
                return "joomla"
            if "drupal.settings" in html or "sites/default/files" in html:
                return "drupal"
            if "magento" in html or "mage.cookies" in html:
                return "magento"
        except Exception:
            pass
        return None

    def _check_wordpress(self, base_url: str) -> list[dict]:
        findings = []

        # Version detection
        try:
            resp = self.session.get(base_url, timeout=10)
            m = re.search(r'<meta name="generator" content="WordPress (\d+\.\d+\.?\d*)"', resp.text)
            if m:
                version = m.group(1)
                findings.append({
                    "type": "wp_version_exposed",
                    "version": version,
                    "detail": f"WordPress version {version} exposed in meta tag",
                    "severity": "low",
                })
        except Exception:
            pass

        # XML-RPC
        try:
            resp = self.session.post(
                f"{base_url}/xmlrpc.php",
                data='<?xml version="1.0"?><methodCall><methodName>system.listMethods</methodName></methodCall>',
                headers={"Content-Type": "text/xml"},
                timeout=8,
            )
            if resp.status_code == 200 and "methodResponse" in resp.text:
                findings.append({
                    "type": "wp_xmlrpc_enabled",
                    "detail": "XML-RPC is enabled — can be used for brute-force and DDoS amplification",
                    "severity": "high",
                })
        except Exception:
            pass

        # User enumeration via REST API
        try:
            resp = self.session.get(f"{base_url}/wp-json/wp/v2/users", timeout=8)
            if resp.status_code == 200:
                users = resp.json()
                if isinstance(users, list) and users:
                    usernames = [u.get("slug", "") for u in users[:5]]
                    findings.append({
                        "type": "wp_user_enumeration",
                        "users": usernames,
                        "detail": f"User enumeration via REST API: {', '.join(usernames)}",
                        "severity": "medium",
                    })
        except Exception:
            pass

        # User enumeration via author parameter
        try:
            for i in range(1, 4):
                resp = self.session.get(f"{base_url}/?author={i}", timeout=5, allow_redirects=True)
                if resp.status_code == 200 and "/author/" in resp.url:
                    findings.append({
                        "type": "wp_author_enumeration",
                        "detail": f"Author enumeration works via ?author={i}",
                        "severity": "low",
                    })
                    break
        except Exception:
            pass

        # wp-login.php accessible
        try:
            resp = self.session.get(f"{base_url}/wp-login.php", timeout=5)
            if resp.status_code == 200:
                findings.append({
                    "type": "wp_login_exposed",
                    "detail": "wp-login.php is publicly accessible",
                    "severity": "low",
                })
        except Exception:
            pass

        # Debug mode
        try:
            resp = self.session.get(f"{base_url}/wp-content/debug.log", timeout=5)
            if resp.status_code == 200 and len(resp.text) > 50:
                findings.append({
                    "type": "wp_debug_log",
                    "detail": "WordPress debug log is publicly accessible",
                    "severity": "high",
                })
        except Exception:
            pass

        # Directory listing
        for path in ["wp-content/uploads/", "wp-content/plugins/", "wp-includes/"]:
            try:
                resp = self.session.get(f"{base_url}/{path}", timeout=5)
                if resp.status_code == 200 and "index of" in resp.text.lower():
                    findings.append({
                        "type": "wp_directory_listing",
                        "path": path,
                        "detail": f"Directory listing enabled at /{path}",
                        "severity": "medium",
                    })
            except Exception:
                pass

        return findings

    def _check_joomla(self, base_url: str) -> list[dict]:
        findings = []

        # Version via manifest
        for path in ["administrator/manifests/files/joomla.xml", "language/en-GB/en-GB.xml"]:
            try:
                resp = self.session.get(f"{base_url}/{path}", timeout=5)
                if resp.status_code == 200:
                    m = re.search(r"<version>([^<]+)</version>", resp.text)
                    if m:
                        findings.append({
                            "type": "joomla_version",
                            "version": m.group(1),
                            "detail": f"Joomla version {m.group(1)} detected via {path}",
                            "severity": "low",
                        })
                        break
            except Exception:
                pass

        # Administrator panel accessible
        try:
            resp = self.session.get(f"{base_url}/administrator/", timeout=5)
            if resp.status_code == 200:
                findings.append({
                    "type": "joomla_admin_exposed",
                    "detail": "Joomla administrator panel is publicly accessible",
                    "severity": "medium",
                })
        except Exception:
            pass

        # Configuration backup
        for path in ["configuration.php.bak", "configuration.php~", "configuration.php.old"]:
            try:
                resp = self.session.get(f"{base_url}/{path}", timeout=5)
                if resp.status_code == 200 and "JConfig" in resp.text:
                    findings.append({
                        "type": "joomla_config_backup",
                        "path": path,
                        "detail": f"Joomla configuration backup accessible at /{path}",
                        "severity": "critical",
                    })
            except Exception:
                pass

        return findings

    def _check_drupal(self, base_url: str) -> list[dict]:
        findings = []

        # Version detection
        try:
            resp = self.session.get(f"{base_url}/CHANGELOG.txt", timeout=5)
            if resp.status_code == 200 and "Drupal" in resp.text:
                m = re.search(r"Drupal (\d+\.\d+)", resp.text)
                if m:
                    findings.append({
                        "type": "drupal_version",
                        "version": m.group(1),
                        "detail": f"Drupal version {m.group(1)} exposed via CHANGELOG.txt",
                        "severity": "medium",
                    })
        except Exception:
            pass

        # User enumeration
        try:
            resp = self.session.get(f"{base_url}/user/1", timeout=5)
            if resp.status_code == 200 and "member for" in resp.text.lower():
                findings.append({
                    "type": "drupal_user_enum",
                    "detail": "User profiles are publicly accessible",
                    "severity": "medium",
                })
        except Exception:
            pass

        # Admin path
        try:
            resp = self.session.get(f"{base_url}/admin", timeout=5, allow_redirects=True)
            if resp.status_code == 200 and "log in" in resp.text.lower():
                findings.append({
                    "type": "drupal_admin_path",
                    "detail": "Default admin path /admin is accessible",
                    "severity": "low",
                })
        except Exception:
            pass

        return findings
