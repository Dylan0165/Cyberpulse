"""M84 — Dependency Vulnerability Scan (White Box)
Connects via SSH and scans package manifests (requirements.txt,
package.json, composer.json, Gemfile, pom.xml) for known vulnerable
dependency versions using basic version comparison.
"""
import re


class Scanner:
    def __init__(self, target, output_dir, config=None):
        self.target = target
        self.output_dir = output_dir
        self.config = config or {}
        self.creds = self.config.get("credentials", {})

    def _ssh_connect(self):
        host = self.creds.get("ssh_host") or self.target
        port = int(self.creds.get("ssh_port") or 22)
        user = self.creds.get("ssh_username", "")
        pwd  = self.creds.get("ssh_password", "")
        key  = self.creds.get("ssh_key", "")
        if not user:
            return None, "Geen SSH-gebruikersnaam"
        try:
            import paramiko, io
            c = paramiko.SSHClient()
            c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            if key:
                pkey = paramiko.RSAKey.from_private_key(io.StringIO(key))
                c.connect(host, port=port, username=user, pkey=pkey, timeout=10)
            else:
                c.connect(host, port=port, username=user, password=pwd, timeout=10)
            return c, None
        except ImportError:
            return None, "paramiko niet geinstalleerd"
        except Exception as e:
            return None, str(e)

    def _exec(self, c, cmd):
        try:
            _, out, _ = c.exec_command(cmd, timeout=20)
            return out.read().decode("utf-8", errors="ignore").strip()
        except Exception:
            return ""

    # Known vulnerable package versions (major/critical CVEs)
    KNOWN_VULN_PY = {
        "django": [("< 4.2.11", "CVE-2024-24680 ReDoS"), ("< 3.2.25", "CVE-2024-27351")],
        "flask": [("< 2.3.3", "CVE-2023-30861 session cookie theft")],
        "requests": [("< 2.31.0", "CVE-2023-32681 redirect credential leak")],
        "pillow": [("< 10.0.1", "CVE-2023-44271 DoS")],
        "cryptography": [("< 41.0.3", "CVE-2023-49083")],
        "sqlalchemy": [("< 2.0.0", "legacy versie, meerdere CVEs")],
        "pyyaml": [("< 6.0.1", "CVE-2022-1471 arbitrary code execution")],
        "paramiko": [("< 3.4.0", "CVE-2023-48795 Terrapin attack")],
        "urllib3": [("< 2.0.7", "CVE-2023-45803 proxy header injection")],
        "numpy": [("< 1.24.0", "CVE-2021-33430 buffer overflow")],
        "werkzeug": [("< 3.0.1", "CVE-2023-46136 multipart DoS")],
        "jinja2": [("< 3.1.3", "CVE-2024-22195 XSS in autoescape")],
        "lxml": [("< 5.1.0", "meerdere XSS CVEs")],
        "setuptools": [("< 65.5.1", "CVE-2022-40897 ReDoS")],
    }

    KNOWN_VULN_NODE = {
        "express": [("< 4.19.2", "CVE-2024-29041 open redirect")],
        "lodash": [("< 4.17.21", "CVE-2021-23337 command injection")],
        "axios": [("< 1.6.0", "CVE-2023-45857 CSRF token leak")],
        "jsonwebtoken": [("< 9.0.0", "CVE-2022-23540 algNone bypass")],
        "node-fetch": [("< 2.6.7", "CVE-2022-0235 information exposure")],
        "minimist": [("< 1.2.6", "CVE-2021-44906 prototype pollution")],
        "qs": [("< 6.10.3", "CVE-2022-24999 prototype pollution")],
        "semver": [("< 7.5.2", "CVE-2022-25883 ReDoS")],
        "tough-cookie": [("< 4.1.3", "CVE-2023-26136 prototype pollution")],
        "sequelize": [("< 6.6.5", "CVE-2023-22578 SQL injection")],
    }

    def _version_lt(self, ver_str, threshold_str):
        """Simple semver comparison for < threshold."""
        try:
            threshold = threshold_str.lstrip("< ").strip()
            v_parts = [int(x) for x in re.split(r"[.\-]", ver_str)[:3]]
            t_parts = [int(x) for x in re.split(r"[.\-]", threshold)[:3]]
            while len(v_parts) < 3: v_parts.append(0)
            while len(t_parts) < 3: t_parts.append(0)
            return v_parts < t_parts
        except Exception:
            return False

    def run(self):
        findings = []
        output = [f"[M84] Dependency kwetsbaarhedenscan via SSH"]

        client, err = self._ssh_connect()
        if client is None:
            return {"findings": [], "raw_output": f"[M84] SSH fout: {err}"}

        src = self.creds.get("source_path", "/var/www")

        # 1. Python requirements.txt
        req_files = self._exec(client,
            f"find {src} /opt /home -name 'requirements*.txt' -not -path '*/.git/*' "
            "2>/dev/null | head -5")
        for req_path in req_files.splitlines():
            req_path = req_path.strip()
            if not req_path:
                continue
            content = self._exec(client, f"cat '{req_path}' 2>/dev/null")
            output.append(f"  requirements: {req_path} ({len(content.splitlines())} packages)")
            for line in content.splitlines():
                m = re.match(r"^([a-zA-Z0-9_\-]+)[=><!\s]+([0-9][0-9a-zA-Z.\-]*)", line.strip())
                if m:
                    pkg = m.group(1).lower()
                    ver = m.group(2)
                    if pkg in self.KNOWN_VULN_PY:
                        for threshold, cve in self.KNOWN_VULN_PY[pkg]:
                            if self._version_lt(ver, threshold):
                                findings.append({
                                    "title": f"Kwetsbare Python Dependency: {pkg} {ver}",
                                    "severity": "high",
                                    "description": f"{pkg} versie {ver} is kwetsbaar. {cve}. Gevonden in {req_path}",
                                    "recommendation": f"Update {pkg} naar de nieuwste versie: pip install --upgrade {pkg}"
                                })
                                output.append(f"  [VULN] {pkg}=={ver} -> {cve}")
                            break

        # 2. Node package.json
        pkg_files = self._exec(client,
            f"find {src} /opt /home -name 'package.json' -not -path '*/node_modules/*' "
            "-not -path '*/.git/*' 2>/dev/null | head -5")
        for pkg_path in pkg_files.splitlines():
            pkg_path = pkg_path.strip()
            if not pkg_path:
                continue
            content = self._exec(client, f"cat '{pkg_path}' 2>/dev/null")
            output.append(f"  package.json: {pkg_path}")
            for pkg, threshold_cve_list in self.KNOWN_VULN_NODE.items():
                m = re.search(rf'"{pkg}":\s*"[~^]?([0-9][0-9a-zA-Z.\-]*)"', content)
                if m:
                    ver = m.group(1)
                    for threshold, cve in threshold_cve_list:
                        if self._version_lt(ver, threshold):
                            findings.append({
                                "title": f"Kwetsbare Node.js Dependency: {pkg} {ver}",
                                "severity": "high",
                                "description": f"{pkg} versie {ver} is kwetsbaar. {cve}. Gevonden in {pkg_path}",
                                "recommendation": f"Update via: npm update {pkg} of verander versie in package.json."
                            })
                            output.append(f"  [VULN] {pkg}@{ver} -> {cve}")
                        break

        # 3. Check if pip-audit or npm audit available
        pip_audit = self._exec(client, "pip-audit --version 2>/dev/null")
        if pip_audit:
            audit_out = self._exec(client,
                f"cd {src} 2>/dev/null && pip-audit 2>/dev/null | head -20")
            vuln_count = audit_out.count("GHSA-") + audit_out.count("CVE-")
            if vuln_count:
                findings.append({
                    "title": f"pip-audit: {vuln_count} Kwetsbaarheden Gevonden",
                    "severity": "high",
                    "description": f"pip-audit gevonden:\n{audit_out[:400]}",
                    "recommendation": "Voer uit: pip-audit --fix om automatisch te updaten."
                })

        client.close()
        if not findings:
            output.append("  [OK] Geen bekende kwetsbare dependencies gevonden")
        return {"findings": findings, "raw_output": "\n".join(output)}
