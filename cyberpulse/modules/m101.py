"""Module 101 — Desktop Binary Analysis.

Static analysis of desktop executables (PE, ELF, Mach-O) for security issues.
"""

import logging
import re
import shutil
import struct
import subprocess
from pathlib import Path

logger = logging.getLogger("cyberpulse.modules.m101")


class Scanner:
    name = "Desktop Binary Analysis"
    phase = "analysis"
    description = "Static security analysis of desktop application binaries"
    target_types = ["desktop"]

    def __init__(self, target: str, output_dir: str, config: dict):
        self.target = target  # Path to binary
        self.output_dir = Path(output_dir)
        self.config = config
        self.timeout = config.get("SCAN_TIMEOUT", 300)

    def _tool_available(self, tool: str) -> bool:
        return shutil.which(tool) is not None

    def run(self) -> dict:
        findings = []
        raw_lines = []
        binary_path = Path(self.target)

        if not binary_path.exists():
            return {
                "findings": [],
                "raw_output": f"Binary niet gevonden: {self.target}",
                "error": "File not found",
            }

        file_type = self._detect_type(binary_path)
        raw_lines.append(f"Binary type: {file_type}")

        if file_type == "PE":
            f, o = self._analyze_pe(binary_path)
            findings.extend(f)
            raw_lines.append(o)
        elif file_type == "ELF":
            f, o = self._analyze_elf(binary_path)
            findings.extend(f)
            raw_lines.append(o)
        elif file_type == "MachO":
            f, o = self._analyze_macho(binary_path)
            findings.extend(f)
            raw_lines.append(o)
        else:
            raw_lines.append("Onbekend binair formaat")

        # Common checks: strings analysis
        f, o = self._strings_analysis(binary_path)
        findings.extend(f)
        raw_lines.append(o)

        raw_lines.append(f"Total findings: {len(findings)}")
        return {"findings": findings, "raw_output": "\n".join(raw_lines), "error": None}

    def _detect_type(self, path: Path) -> str:
        """Detect binary type from magic bytes."""
        try:
            with open(path, "rb") as f:
                magic = f.read(4)
                if magic[:2] == b"MZ":
                    return "PE"
                if magic[:4] == b"\x7fELF":
                    return "ELF"
                if magic[:4] in (b"\xfe\xed\xfa\xce", b"\xfe\xed\xfa\xcf",
                                  b"\xce\xfa\xed\xfe", b"\xcf\xfa\xed\xfe"):
                    return "MachO"
        except Exception:
            pass
        return "unknown"

    def _analyze_pe(self, binary_path: Path) -> tuple:
        """Analyze Windows PE binary for security features."""
        findings = []
        raw_lines = []

        try:
            with open(binary_path, "rb") as f:
                # Read DOS header
                f.seek(0x3C)
                pe_offset = struct.unpack("<I", f.read(4))[0]

                # Read PE signature
                f.seek(pe_offset)
                signature = f.read(4)
                if signature != b"PE\x00\x00":
                    return findings, "Ongeldig PE bestand"

                # Read COFF header
                f.read(2)  # Machine
                f.read(2)  # NumberOfSections
                f.read(4)  # TimeDateStamp
                f.read(4)  # PointerToSymbolTable
                f.read(4)  # NumberOfSymbols
                optional_size = struct.unpack("<H", f.read(2))[0]
                characteristics = struct.unpack("<H", f.read(2))[0]

                raw_lines.append(f"PE characteristics: 0x{characteristics:04X}")

                # Check DLL characteristics in Optional Header
                if optional_size > 0:
                    magic = struct.unpack("<H", f.read(2))[0]
                    is_64 = magic == 0x20B

                    # Skip to DllCharacteristics
                    if is_64:
                        f.seek(pe_offset + 24 + 70)  # PE64 DllCharacteristics offset
                    else:
                        f.seek(pe_offset + 24 + 46)  # PE32 DllCharacteristics offset

                    dll_chars = struct.unpack("<H", f.read(2))[0]
                    raw_lines.append(f"DLL characteristics: 0x{dll_chars:04X}")

                    # ASLR check (IMAGE_DLLCHARACTERISTICS_DYNAMIC_BASE = 0x0040)
                    if not (dll_chars & 0x0040):
                        findings.append({
                            "type": "no_aslr",
                            "severity": "high",
                            "detail": "ASLR (Address Space Layout Randomization) is niet ingeschakeld",
                        })

                    # DEP check (IMAGE_DLLCHARACTERISTICS_NX_COMPAT = 0x0100)
                    if not (dll_chars & 0x0100):
                        findings.append({
                            "type": "no_dep",
                            "severity": "high",
                            "detail": "DEP/NX (Data Execution Prevention) is niet ingeschakeld",
                        })

                    # CFG check (IMAGE_DLLCHARACTERISTICS_GUARD_CF = 0x4000)
                    if not (dll_chars & 0x4000):
                        findings.append({
                            "type": "no_cfg",
                            "severity": "medium",
                            "detail": "Control Flow Guard (CFG) is niet ingeschakeld",
                        })

                    # High entropy ASLR (IMAGE_DLLCHARACTERISTICS_HIGH_ENTROPY_VA = 0x0020)
                    if is_64 and not (dll_chars & 0x0020):
                        findings.append({
                            "type": "no_high_entropy_aslr",
                            "severity": "medium",
                            "detail": "High Entropy ASLR is niet ingeschakeld (64-bit binary)",
                        })

            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)

    def _analyze_elf(self, binary_path: Path) -> tuple:
        """Analyze Linux ELF binary for security features."""
        findings = []
        raw_lines = []

        # Use checksec if available
        if self._tool_available("checksec"):
            try:
                result = subprocess.run(
                    ["checksec", "--file", str(binary_path), "--output", "json"],
                    capture_output=True, text=True, timeout=30,
                )
                import json
                data = json.loads(result.stdout)
                file_data = list(data.values())[0] if data else {}

                if file_data.get("canary") == "no":
                    findings.append({
                        "type": "no_stack_canary",
                        "severity": "high",
                        "detail": "Stack canary (stack protector) is niet ingeschakeld",
                    })

                if file_data.get("nx") == "no":
                    findings.append({
                        "type": "no_nx",
                        "severity": "high",
                        "detail": "NX bit is niet ingeschakeld — stack is uitvoerbaar",
                    })

                if file_data.get("pie") == "no":
                    findings.append({
                        "type": "no_pie",
                        "severity": "high",
                        "detail": "PIE (Position Independent Executable) is niet ingeschakeld",
                    })

                if file_data.get("relro") == "no":
                    findings.append({
                        "type": "no_relro",
                        "severity": "medium",
                        "detail": "RELRO is niet ingeschakeld — GOT kan overschreven worden",
                    })
                elif file_data.get("relro") == "partial":
                    findings.append({
                        "type": "partial_relro",
                        "severity": "low",
                        "detail": "Alleen partial RELRO — full RELRO wordt aanbevolen",
                    })

                raw_lines.append(f"checksec output: {file_data}")
                return findings, "\n".join(raw_lines)

            except Exception as e:
                raw_lines.append(f"checksec fout: {e}")

        # Fallback: manual readelf analysis
        if self._tool_available("readelf"):
            try:
                result = subprocess.run(
                    ["readelf", "-l", str(binary_path)],
                    capture_output=True, text=True, timeout=30,
                )
                output = result.stdout

                if "GNU_STACK" in output:
                    for line in output.splitlines():
                        if "GNU_STACK" in line and "RWE" in line:
                            findings.append({
                                "type": "executable_stack",
                                "severity": "high",
                                "detail": "Stack is gemarkeerd als uitvoerbaar (RWE)",
                            })

                if "GNU_RELRO" not in output:
                    findings.append({
                        "type": "no_relro",
                        "severity": "medium",
                        "detail": "RELRO is niet ingeschakeld",
                    })

                raw_lines.append("readelf analyse voltooid")

            except Exception as e:
                raw_lines.append(str(e))

        return findings, "\n".join(raw_lines)

    def _analyze_macho(self, binary_path: Path) -> tuple:
        """Analyze macOS Mach-O binary."""
        findings = []
        raw_lines = []

        if self._tool_available("otool"):
            try:
                # Check PIE
                result = subprocess.run(
                    ["otool", "-hv", str(binary_path)],
                    capture_output=True, text=True, timeout=30,
                )
                if "PIE" not in result.stdout:
                    findings.append({
                        "type": "no_pie",
                        "severity": "high",
                        "detail": "Binary is niet PIE — ASLR niet effectief",
                    })

                # Check stack canary
                result = subprocess.run(
                    ["otool", "-Iv", str(binary_path)],
                    capture_output=True, text=True, timeout=30,
                )
                if "___stack_chk" not in result.stdout:
                    findings.append({
                        "type": "no_stack_canary",
                        "severity": "high",
                        "detail": "Stack canary is niet gevonden in binary",
                    })

                # Check code signing
                if self._tool_available("codesign"):
                    result = subprocess.run(
                        ["codesign", "-dv", str(binary_path)],
                        capture_output=True, text=True, timeout=30,
                    )
                    if result.returncode != 0:
                        findings.append({
                            "type": "not_signed",
                            "severity": "medium",
                            "detail": "Binary is niet code-signed",
                        })

                raw_lines.append("Mach-O analyse voltooid")

            except Exception as e:
                raw_lines.append(str(e))

        return findings, "\n".join(raw_lines)

    def _strings_analysis(self, binary_path: Path) -> tuple:
        """Search binary strings for hardcoded secrets and dangerous patterns."""
        findings = []
        raw_lines = []

        secret_patterns = [
            (r'(?i)(password|passwd|pwd)\s*=\s*["\']([^"\']{4,})', "hardcoded_password", "critical"),
            (r'(?i)(api[_-]?key|apikey)\s*=\s*["\']([^"\']{16,})', "hardcoded_api_key", "high"),
            (r'(?i)-----BEGIN\s+(RSA|EC)?\s*PRIVATE\s+KEY-----', "embedded_private_key", "critical"),
            (r'(?i)(secret|token)\s*=\s*["\']([^"\']{16,})', "hardcoded_secret", "high"),
        ]

        try:
            if self._tool_available("strings"):
                result = subprocess.run(
                    ["strings", "-n", "8", str(binary_path)],
                    capture_output=True, text=True, timeout=30,
                )
                content = result.stdout
            else:
                # Fallback: read file and extract printable strings
                data = binary_path.read_bytes()
                content = "".join(
                    chr(b) if 32 <= b < 127 else "\n"
                    for b in data
                )

            for pattern, finding_type, severity in secret_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    findings.append({
                        "type": finding_type,
                        "severity": severity,
                        "detail": f"Mogelijk hardcoded {finding_type.replace('_', ' ')} gevonden in binary",
                    })

            # Check for dangerous function usage
            dangerous_funcs = {
                "strcpy": ("unsafe_strcpy", "medium", "Gebruik van strcpy() — buffer overflow risico"),
                "strcat": ("unsafe_strcat", "medium", "Gebruik van strcat() — buffer overflow risico"),
                "sprintf": ("unsafe_sprintf", "medium", "Gebruik van sprintf() — buffer overflow risico"),
                "gets": ("unsafe_gets", "high", "Gebruik van gets() — ernstig buffer overflow risico"),
            }

            for func, (ftype, sev, detail) in dangerous_funcs.items():
                if func in content:
                    findings.append({
                        "type": ftype,
                        "severity": sev,
                        "detail": detail,
                    })

            raw_lines.append(f"Strings analyse: {len(findings)} bevindingen")
            return findings, "\n".join(raw_lines)

        except Exception as e:
            return findings, str(e)
