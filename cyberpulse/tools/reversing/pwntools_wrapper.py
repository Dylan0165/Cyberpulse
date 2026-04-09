"""Pwntools — CTF/exploit development framework (Python native)."""

from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class PwntoolsWrapper(BaseToolWrapper):
    name = "pwntools"
    display_name = "Pwntools"
    category = ToolCategory.REVERSING
    implementation = ImplementationMethod.PYTHON_NATIVE
    default_timeout = 60
    resource_profile = ResourceProfile(estimated_ram_mb=64, estimated_duration_s=10)

    def is_available(self) -> bool:
        try:
            import pwn  # noqa: F401
            return True
        except ImportError:
            return False

    def build_command(self, target: str, **kwargs) -> list[str]:
        return []

    def run_native(self, target: str, **kwargs) -> tuple[str, str]:
        """Analyse binary security properties using checksec."""
        from pwn import ELF
        elf = ELF(target, checksec=False)
        info = {
            "arch": elf.arch,
            "bits": elf.bits,
            "canary": elf.canary,
            "nx": elf.nx,
            "pie": elf.pie,
            "relro": str(elf.relro) if hasattr(elf, 'relro') else "unknown",
        }
        import json
        return json.dumps(info, indent=2), ""

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        import json
        try:
            info = json.loads(stdout)
            if not info.get("canary"):
                findings.append(ToolFinding(tool=self.name, title="Geen Stack Canary", detail="Binary mist stack canary protectie.", severity=Severity.HIGH, recommendation="Compileer met -fstack-protector-all."))
            if not info.get("nx"):
                findings.append(ToolFinding(tool=self.name, title="NX uitgeschakeld", detail="Executable stack.", severity=Severity.HIGH, recommendation="Activeer NX/DEP."))
            if not info.get("pie"):
                findings.append(ToolFinding(tool=self.name, title="Geen PIE", detail="Binary is niet position-independent.", severity=Severity.MEDIUM, recommendation="Compileer met -fPIE -pie."))
            if info.get("relro") in ("No RELRO", "Partial"):
                findings.append(ToolFinding(tool=self.name, title=f"RELRO: {info['relro']}", detail="Onvolledige RELRO protectie.", severity=Severity.MEDIUM, recommendation="Compileer met -Wl,-z,relro,-z,now."))
        except (json.JSONDecodeError, TypeError):
            pass
        return findings
