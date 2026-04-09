"""Hash-identifier — fallback hash type identification."""

import re
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

# Common hash patterns
HASH_PATTERNS = {
    r"^[a-f0-9]{32}$": ("MD5", Severity.MEDIUM),
    r"^[a-f0-9]{40}$": ("SHA-1", Severity.MEDIUM),
    r"^[a-f0-9]{64}$": ("SHA-256", Severity.LOW),
    r"^[a-f0-9]{128}$": ("SHA-512", Severity.INFO),
    r"^\$2[aby]?\$\d+\$.{53}$": ("bcrypt", Severity.INFO),
    r"^\$6\$": ("SHA-512 Crypt (Unix)", Severity.INFO),
    r"^\$5\$": ("SHA-256 Crypt (Unix)", Severity.LOW),
    r"^\$1\$": ("MD5 Crypt (Unix)", Severity.MEDIUM),
    r"^\$argon2": ("Argon2", Severity.INFO),
    r"^[a-f0-9]{16}$": ("MySQL 3.23 / Half MD5", Severity.HIGH),
    r"^\*[A-F0-9]{40}$": ("MySQL 4.1+", Severity.MEDIUM),
    r"^[a-f0-9]{32}:[a-f0-9]+$": ("MD5 (salted)", Severity.MEDIUM),
}


@register
class HashIdentifierWrapper(BaseToolWrapper):
    name = "hash_identifier"
    display_name = "Hash Identifier"
    category = ToolCategory.CRYPTO
    implementation = ImplementationMethod.PYTHON_NATIVE
    python_dependencies = []  # No deps — pure Python fallback
    default_timeout = 10
    resource_profile = ResourceProfile(estimated_ram_mb=16, estimated_duration_s=1)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return []

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        return []

    def run_native(self, target: str, output_dir=None, **kwargs) -> list[ToolFinding]:
        hash_value = kwargs.get("hash_value", target).strip()
        findings = []

        matched = False
        for pattern, (name, severity) in HASH_PATTERNS.items():
            if re.match(pattern, hash_value, re.IGNORECASE):
                matched = True
                findings.append(ToolFinding(
                    tool=self.name,
                    title=f"Hash type: {name}",
                    detail=f"Hash geïdentificeerd als {name}",
                    severity=severity,
                    description=f"De hash '{hash_value[:30]}...' is geïdentificeerd als {name}.",
                    recommendation="Gebruik bcrypt of Argon2 voor wachtwoord hashing." if severity != Severity.INFO else "Hash algoritme is veilig.",
                    raw_output=f"{hash_value[:50]} → {name}",
                ))
                break

        if not matched:
            findings.append(ToolFinding(
                tool=self.name,
                title="Hash type onbekend",
                detail=f"Kon het hash type niet bepalen (lengte: {len(hash_value)})",
                severity=Severity.INFO,
                raw_output=hash_value[:50],
            ))

        return findings
