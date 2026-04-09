"""Module 98b — Android APK Analysis.

Static analysis of Android APK files for security issues.
"""

import json
import logging
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m98b")

# Dangerous Android permissions
DANGEROUS_PERMISSIONS = {
    "android.permission.READ_SMS": "high",
    "android.permission.SEND_SMS": "high",
    "android.permission.READ_CONTACTS": "medium",
    "android.permission.READ_CALL_LOG": "high",
    "android.permission.CAMERA": "medium",
    "android.permission.RECORD_AUDIO": "high",
    "android.permission.ACCESS_FINE_LOCATION": "medium",
    "android.permission.READ_EXTERNAL_STORAGE": "medium",
    "android.permission.WRITE_EXTERNAL_STORAGE": "medium",
    "android.permission.INSTALL_PACKAGES": "critical",
    "android.permission.SYSTEM_ALERT_WINDOW": "high",
}


class Scanner:
    name = "Android APK Analysis"
    phase = "analysis"
    description = "Static security analysis of Android APK files"
    target_types = ["mobile_android"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target  # Path to APK file
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 600)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        findings = []
        raw_lines = []
        apk_path = Path(self.target)

        if not apk_path.exists() or not apk_path.suffix.lower() == ".apk":
            return {
                "findings": [],
                "raw_output": f"APK bestand niet gevonden of ongeldig: {self.target}",
                "error": "Invalid APK path",
            }

        # Step 1: Extract manifest with aapt
        if self._tool_available("aapt"):
            f, o = self._analyze_manifest(apk_path)
            findings.extend(f)
            raw_lines.append(o)

        # Step 2: Check for hardcoded secrets in APK
        f, o = self._scan_apk_contents(apk_path)
        findings.extend(f)
        raw_lines.append(o)

        # Step 3: Use apktool if available
        if self._tool_available("apktool"):
            f, o = self._decompile_analysis(apk_path)
            findings.extend(f)
            raw_lines.append(o)

        # Step 4: Use jadx for deeper analysis
        if self._tool_available("jadx"):
            f, o = self._jadx_analysis(apk_path)
            findings.extend(f)
            raw_lines.append(o)

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _analyze_manifest(self, apk_path: Path) -> tuple:
        findings = []
        try:
            result = subprocess.run(
                ["aapt", "dump", "badging", str(apk_path)],
                capture_output=True, text=True, timeout=60,
            )
            output = result.stdout

            # Check debuggable
            if "application-debuggable" in output:
                findings.append({
                    "type": "debuggable_app",
                    "severity": "high",
                    "detail": "APK is debuggable — kan misbruikt worden voor runtime inspectie",
                })

            # Check backup allowed
            if "allowBackup='true'" in output or "allowBackup" not in output:
                findings.append({
                    "type": "backup_allowed",
                    "severity": "medium",
                    "detail": "App backup is toegestaan — data kan geëxtraheerd worden via adb backup",
                })

            # Check min SDK
            sdk_match = re.search(r"sdkVersion:'(\d+)'", output)
            if sdk_match:
                min_sdk = int(sdk_match.group(1))
                if min_sdk < 21:
                    findings.append({
                        "type": "low_min_sdk",
                        "severity": "medium",
                        "detail": f"Minimale SDK versie is {min_sdk} — mist moderne beveiligingsfuncties",
                        "min_sdk": min_sdk,
                    })

            # Check permissions
            for perm_match in re.finditer(r"uses-permission: name='([^']+)'", output):
                perm = perm_match.group(1)
                if perm in DANGEROUS_PERMISSIONS:
                    findings.append({
                        "type": "dangerous_permission",
                        "severity": DANGEROUS_PERMISSIONS[perm],
                        "detail": f"Gevaarlijke permissie: {perm}",
                        "permission": perm,
                    })

            return findings, output[:2000]

        except (subprocess.TimeoutExpired, Exception) as e:
            return findings, str(e)

    def _scan_apk_contents(self, apk_path: Path) -> tuple:
        """Scan APK ZIP contents for hardcoded secrets."""
        findings = []
        raw_lines = []

        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*=\s*"([^"]{16,})"', "api_key"),
            (r'(?i)(password|passwd)\s*=\s*"([^"]{4,})"', "password"),
            (r'(?i)firebase.*\.com', "firebase_url"),
            (r'AIza[0-9A-Za-z_-]{35}', "google_api_key"),
            (r'(?i)-----BEGIN\s+(RSA|EC)?\s*PRIVATE\s+KEY-----', "private_key"),
        ]

        try:
            with zipfile.ZipFile(str(apk_path), "r") as zf:
                for name in zf.namelist():
                    if name.endswith((".xml", ".json", ".properties", ".txt", ".js")):
                        try:
                            content = zf.read(name).decode("utf-8", errors="ignore")
                            for pattern, secret_type in secret_patterns:
                                if re.search(pattern, content):
                                    findings.append({
                                        "type": "hardcoded_secret",
                                        "severity": "critical" if secret_type == "private_key" else "high",
                                        "detail": f"Hardcoded {secret_type} gevonden in {name}",
                                        "file": name,
                                        "secret_type": secret_type,
                                    })
                                    break
                        except Exception:
                            continue

                    # Check for cert files
                    if name.endswith((".p12", ".pfx", ".jks", ".bks", ".pem")):
                        findings.append({
                            "type": "embedded_certificate",
                            "severity": "medium",
                            "detail": f"Ingebed certificaat gevonden: {name}",
                            "file": name,
                        })

            raw_lines.append(f"APK inhoud gescand — {len(findings)} bevindingen")
            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)

    def _decompile_analysis(self, apk_path: Path) -> tuple:
        """Decompile APK with apktool for deeper analysis."""
        findings = []
        decompile_dir = self.output_dir / "apktool_out"

        try:
            result = subprocess.run(
                ["apktool", "d", "-f", "-o", str(decompile_dir), str(apk_path)],
                capture_output=True, text=True, timeout=self.timeout,
            )

            # Check network security config
            nsc_path = decompile_dir / "res" / "xml" / "network_security_config.xml"
            if nsc_path.exists():
                nsc_content = nsc_path.read_text(encoding="utf-8", errors="ignore")
                if "cleartextTrafficPermitted=\"true\"" in nsc_content:
                    findings.append({
                        "type": "cleartext_traffic",
                        "severity": "high",
                        "detail": "Cleartext (HTTP) verkeer is toegestaan in network security config",
                    })
                if "<certificates src=\"user\"" in nsc_content:
                    findings.append({
                        "type": "user_certificates_trusted",
                        "severity": "medium",
                        "detail": "App vertrouwt door gebruiker geïnstalleerde certificaten",
                    })

            return findings, result.stdout[:1000]

        except (subprocess.TimeoutExpired, Exception) as e:
            return findings, str(e)

    def _jadx_analysis(self, apk_path: Path) -> tuple:
        """Decompile to Java with jadx for code analysis."""
        findings = []
        jadx_dir = self.output_dir / "jadx_out"

        try:
            result = subprocess.run(
                ["jadx", "--no-res", "-d", str(jadx_dir), str(apk_path)],
                capture_output=True, text=True, timeout=self.timeout,
            )

            # Search decompiled Java for insecure patterns
            insecure_patterns = [
                (r'TrustManager.*\{[^}]*\}', "ssl_bypass", "high",
                 "Custom TrustManager gevonden — mogelijk SSL certificaat validatie bypass"),
                (r'WebView.*setJavaScriptEnabled\(true\)', "webview_js", "medium",
                 "WebView met JavaScript ingeschakeld — XSS risico"),
                (r'MODE_WORLD_READABLE|MODE_WORLD_WRITEABLE', "world_access", "high",
                 "Bestanden met world-readable/writable permissies"),
                (r'Log\.(d|v|i)\([^)]*password|Log\.(d|v|i)\([^)]*token', "log_sensitive", "high",
                 "Gevoelige data wordt gelogd"),
            ]

            if jadx_dir.exists():
                for java_file in jadx_dir.rglob("*.java"):
                    try:
                        content = java_file.read_text(encoding="utf-8", errors="ignore")
                        for pattern, finding_type, severity, detail in insecure_patterns:
                            if re.search(pattern, content, re.DOTALL):
                                findings.append({
                                    "type": finding_type,
                                    "severity": severity,
                                    "detail": f"{detail} in {java_file.name}",
                                    "file": str(java_file.relative_to(jadx_dir)),
                                })
                    except Exception:
                        continue

            return findings, result.stdout[:1000]

        except (subprocess.TimeoutExpired, Exception) as e:
            return findings, str(e)
