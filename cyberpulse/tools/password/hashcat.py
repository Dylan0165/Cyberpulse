"""Hashcat — GPU/CPU password cracker with automatic fallback."""

import re
import shutil
import subprocess
from pathlib import Path

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


def _detect_gpu() -> bool:
    """Check if a compatible GPU is available for Hashcat."""
    try:
        result = subprocess.run(
            ["hashcat", "--opencl-info"],
            capture_output=True, text=True, timeout=10,
        )
        return "Device" in result.stdout
    except Exception:
        pass
    try:
        result = subprocess.run(
            ["nvidia-smi"],
            capture_output=True, text=True, timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False


@register
class HashcatWrapper(BaseToolWrapper):
    name = "hashcat"
    display_name = "Hashcat"
    category = ToolCategory.PASSWORD_CRACKING
    implementation = ImplementationMethod.SUBPROCESS
    required_binaries = ["hashcat"]
    default_timeout = 300
    resource_profile = ResourceProfile(
        estimated_ram_mb=512, estimated_duration_s=300,
        requires_gpu=False, cpu_intensive=True,
    )

    def build_command(self, target: str, **kwargs) -> list[str]:
        hashfile = kwargs.get("hashfile", target)
        hash_mode = kwargs.get("hash_mode", "0")  # 0 = MD5
        wordlist = kwargs.get("wordlist", "")

        cmd = ["hashcat", "-m", str(hash_mode)]

        if _detect_gpu():
            cmd.extend(["-d", "1", "-w", "2"])  # GPU, workload medium
        else:
            cmd.extend(["--force", "-D", "1"])  # CPU-only fallback

        cmd.extend(["--status", "--status-timer=10", "--potfile-disable"])

        if wordlist:
            cmd.extend([str(hashfile), str(wordlist)])
        else:
            cmd.extend([str(hashfile)])

        return cmd

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        combined = stdout + "\n" + stderr

        # Parse cracked hashes: "hash:password"
        for line in combined.splitlines():
            if ":" in line and not line.startswith("[") and not line.startswith("Session"):
                parts = line.strip().split(":", 1)
                if len(parts) == 2 and len(parts[1]) > 0 and len(parts[1]) < 128:
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"Hash gekraakt",
                        detail=f"Hashcat heeft een wachtwoord-hash succesvol gekraakt",
                        severity=Severity.HIGH,
                        description="Hashcat kon de hash kraken met de opgegeven woordenlijst. "
                                    "Dit duidt op een zwak wachtwoord.",
                        recommendation="Gebruik sterkere wachtwoorden en moderne hash algoritmes (bcrypt/argon2).",
                        raw_output=line.strip()[:200],
                    ))

        # Check for status info
        if "Recovered" in combined:
            match = re.search(r"Recovered\.+:\s*(\d+)/(\d+)", combined)
            if match:
                cracked, total = int(match.group(1)), int(match.group(2))
                if cracked > 0:
                    pct = (cracked / total * 100) if total > 0 else 0
                    findings.append(ToolFinding(
                        tool=self.name,
                        title=f"{cracked}/{total} hashes gekraakt ({pct:.0f}%)",
                        detail=f"Hashcat kraakte {cracked} van {total} hashes",
                        severity=Severity.HIGH if pct > 50 else Severity.MEDIUM,
                        description=f"Van de {total} aangeboden hashes zijn er {cracked} gekraakt.",
                        recommendation="Verander alle gekraakte wachtwoorden. Implementeer een sterk wachtwoordbeleid.",
                    ))

        return findings
