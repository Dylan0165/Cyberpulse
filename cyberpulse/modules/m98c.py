"""Module 98c — iOS IPA Analysis.

Static analysis of iOS IPA files for security issues.
"""

import json
import logging
import plistlib
import re
import shutil
import subprocess
import zipfile
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m98c")


class Scanner:
    name = "iOS IPA Analysis"
    phase = "analysis"
    description = "Static security analysis of iOS IPA files"
    target_types = ["mobile_ios"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target  # Path to IPA file
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 600)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        findings = []
        raw_lines = []
        ipa_path = Path(self.target)

        if not ipa_path.exists() or not ipa_path.suffix.lower() == ".ipa":
            return {
                "findings": [],
                "raw_output": f"IPA bestand niet gevonden of ongeldig: {self.target}",
                "error": "Invalid IPA path",
            }

        # Step 1: Extract and analyze Info.plist
        f, o = self._analyze_plist(ipa_path)
        findings.extend(f)
        raw_lines.append(o)

        # Step 2: Check for hardcoded secrets
        f, o = self._scan_ipa_contents(ipa_path)
        findings.extend(f)
        raw_lines.append(o)

        # Step 3: Binary analysis if otool available
        if self._tool_available("otool"):
            f, o = self._binary_analysis(ipa_path)
            findings.extend(f)
            raw_lines.append(o)

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _analyze_plist(self, ipa_path: Path) -> tuple:
        """Extract and analyze Info.plist from IPA."""
        findings = []
        raw_lines = []

        try:
            with zipfile.ZipFile(str(ipa_path), "r") as zf:
                # Find Info.plist inside the .app bundle
                plist_path = None
                for name in zf.namelist():
                    if name.endswith(".app/Info.plist"):
                        plist_path = name
                        break

                if not plist_path:
                    return findings, "Info.plist niet gevonden in IPA"

                plist_data = zf.read(plist_path)
                try:
                    plist = plistlib.loads(plist_data)
                except Exception:
                    return findings, "Kon Info.plist niet parsen"

                raw_lines.append(f"Bundle ID: {plist.get('CFBundleIdentifier', 'unknown')}")
                raw_lines.append(f"Version: {plist.get('CFBundleShortVersionString', 'unknown')}")

                # Check ATS (App Transport Security)
                ats = plist.get("NSAppTransportSecurity", {})
                if ats.get("NSAllowsArbitraryLoads"):
                    findings.append({
                        "type": "ats_disabled",
                        "severity": "high",
                        "detail": "App Transport Security is uitgeschakeld — HTTP verkeer toegestaan",
                    })

                ats_exceptions = ats.get("NSExceptionDomains", {})
                for domain, config in ats_exceptions.items():
                    if config.get("NSExceptionAllowsInsecureHTTPLoads"):
                        findings.append({
                            "type": "ats_exception",
                            "severity": "medium",
                            "detail": f"ATS uitzondering voor {domain} — HTTP toegestaan",
                            "domain": domain,
                        })

                # Check URL schemes
                url_types = plist.get("CFBundleURLTypes", [])
                for url_type in url_types:
                    schemes = url_type.get("CFBundleURLSchemes", [])
                    for scheme in schemes:
                        raw_lines.append(f"URL scheme: {scheme}://")
                        if scheme in ("http", "https"):
                            continue
                        findings.append({
                            "type": "custom_url_scheme",
                            "severity": "info",
                            "detail": f"Custom URL scheme geregistreerd: {scheme}://",
                            "scheme": scheme,
                        })

                # Check for background modes
                bg_modes = plist.get("UIBackgroundModes", [])
                sensitive_modes = {"location", "audio", "bluetooth-central"}
                for mode in bg_modes:
                    if mode in sensitive_modes:
                        findings.append({
                            "type": "background_mode",
                            "severity": "info",
                            "detail": f"Achtergrond modus actief: {mode}",
                            "mode": mode,
                        })

                # Check minimum OS version
                min_os = plist.get("MinimumOSVersion", "")
                if min_os:
                    try:
                        major = int(min_os.split(".")[0])
                        if major < 14:
                            findings.append({
                                "type": "low_min_os",
                                "severity": "medium",
                                "detail": f"Minimale iOS versie is {min_os} — mist moderne beveiligingsfuncties",
                                "min_os": min_os,
                            })
                    except ValueError:
                        pass

            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)

    def _scan_ipa_contents(self, ipa_path: Path) -> tuple:
        """Scan IPA contents for secrets and sensitive files."""
        findings = []
        raw_lines = []

        secret_patterns = [
            (r'(?i)(api[_-]?key|apikey)\s*=\s*@?"([^"]{16,})"', "api_key"),
            (r'(?i)(password|passwd)\s*=\s*@?"([^"]{4,})"', "password"),
            (r'AIza[0-9A-Za-z_-]{35}', "google_api_key"),
            (r'(?i)-----BEGIN\s+(RSA|EC)?\s*PRIVATE\s+KEY-----', "private_key"),
            (r'(?i)firebase.*\.com', "firebase_url"),
        ]

        try:
            with zipfile.ZipFile(str(ipa_path), "r") as zf:
                for name in zf.namelist():
                    # Check text files
                    if name.endswith((".plist", ".json", ".xml", ".strings", ".js")):
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
                    if name.endswith((".p12", ".pfx", ".cer", ".pem", ".der")):
                        findings.append({
                            "type": "embedded_certificate",
                            "severity": "medium",
                            "detail": f"Ingebed certificaat gevonden: {name}",
                            "file": name,
                        })

                    # Check for SQLite databases
                    if name.endswith((".sqlite", ".db", ".sqlite3")):
                        findings.append({
                            "type": "embedded_database",
                            "severity": "medium",
                            "detail": f"Ingebedde database gevonden: {name}",
                            "file": name,
                        })

            raw_lines.append(f"IPA inhoud gescand — {len(findings)} bevindingen")
            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)

    def _binary_analysis(self, ipa_path: Path) -> tuple:
        """Analyze the main binary with otool."""
        findings = []
        raw_lines = []

        try:
            # Extract the binary
            with zipfile.ZipFile(str(ipa_path), "r") as zf:
                app_dir = None
                for name in zf.namelist():
                    if name.count("/") == 2 and name.endswith(".app/"):
                        app_dir = name
                        break

                if not app_dir:
                    return findings, "Geen .app bundle gevonden"

                # Find main binary
                plist_path = None
                for name in zf.namelist():
                    if name.endswith(".app/Info.plist"):
                        plist_path = name
                        break

                if not plist_path:
                    return findings, "Info.plist niet gevonden"

                plist = plistlib.loads(zf.read(plist_path))
                executable_name = plist.get("CFBundleExecutable", "")
                binary_path = app_dir + executable_name

                if binary_path not in zf.namelist():
                    return findings, f"Binary niet gevonden: {binary_path}"

                extract_path = self.output_dir / "ios_binary"
                extract_path.mkdir(exist_ok=True)
                binary_file = extract_path / executable_name
                binary_file.write_bytes(zf.read(binary_path))

            # Check PIE (Position Independent Executable)
            result = subprocess.run(
                ["otool", "-hv", str(binary_file)],
                capture_output=True, text=True, timeout=30,
            )
            if "PIE" not in result.stdout:
                findings.append({
                    "type": "no_pie",
                    "severity": "high",
                    "detail": "Binary is niet gecompileerd als PIE — ASLR niet effectief",
                })

            # Check for ARC
            result = subprocess.run(
                ["otool", "-l", str(binary_file)],
                capture_output=True, text=True, timeout=30,
            )
            if "objc_release" not in result.stdout:
                findings.append({
                    "type": "no_arc",
                    "severity": "medium",
                    "detail": "Binary gebruikt mogelijk geen ARC — geheugen kwetsbaarheidsrisico",
                })

            raw_lines.append(f"Binary analyse voltooid voor {executable_name}")
            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)
