"""Hashid — hash type identification (Python native)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register

WEAK_ALGORITHMS = {"MD5", "MD4", "SHA-1", "SHA1", "NTLM", "LM", "DES", "MySQL323"}
STRONG_ALGORITHMS = {"bcrypt", "scrypt", "Argon2", "PBKDF2", "SHA-512"}


@register
class HashidWrapper(BaseToolWrapper):
    name = "hashid"
    display_name = "Hashid"
    category = ToolCategory.CRYPTO
    implementation = ImplementationMethod.PYTHON_NATIVE
    python_dependencies = ["hashid"]
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=5)

    def build_command(self, target: str, **kwargs) -> list[str]:
        return []  # Python native, no subprocess

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        return []  # Not used for native

    def run_native(self, target: str, output_dir=None, **kwargs) -> list[ToolFinding]:
        findings = []
        hash_value = kwargs.get("hash_value", target)

        try:
            from hashid import HashID

            hid = HashID()
            possible_types = list(hid.identifyHash(hash_value))

            if not possible_types:
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Hash type niet geïdentificeerd",
                    detail=f"Hashid kon het type niet bepalen voor: {hash_value[:50]}",
                    severity=Severity.INFO,
                ))
                return findings

            type_names = [ht.name for ht in possible_types[:5]]
            is_weak = any(wk in name for name in type_names for wk in WEAK_ALGORITHMS)
            is_strong = any(st in name for name in type_names for st in STRONG_ALGORITHMS)

            if is_weak:
                severity = Severity.MEDIUM
                desc = "Het hash algoritme is zwak en kan eenvoudig gekraakt worden."
                rec = "Migreer naar een sterk hash algoritme (bcrypt, argon2, PBKDF2)."
            elif is_strong:
                severity = Severity.INFO
                desc = "Het hash algoritme is sterk."
                rec = "Geen actie vereist — het gebruikte algoritme is veilig."
            else:
                severity = Severity.LOW
                desc = "Het hash algoritme is geïdentificeerd."
                rec = "Controleer of het gebruikte hash algoritme geschikt is voor het doel."

            findings.append(ToolFinding(
                tool=self.name,
                title=f"Hash type: {type_names[0]}",
                detail=f"Mogelijke types: {', '.join(type_names)}",
                severity=severity,
                description=desc,
                recommendation=rec,
                raw_output=f"Hash: {hash_value[:50]}... → {', '.join(type_names)}",
            ))

        except ImportError:
            findings.append(ToolFinding(
                tool=self.name,
                title="Hashid niet beschikbaar",
                detail="Python package 'hashid' is niet geïnstalleerd",
                severity=Severity.INFO,
            ))

        return findings
