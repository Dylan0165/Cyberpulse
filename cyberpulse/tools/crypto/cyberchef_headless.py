"""CyberChef headless — data encoding/decoding via Node.js CyberChef."""

import json
from tools.base import (
    BaseToolWrapper, ImplementationMethod, ResourceProfile,
    Severity, ToolCategory, ToolFinding,
)
from tools.tool_runner import register


@register
class CyberchefWrapper(BaseToolWrapper):
    name = "cyberchef"
    display_name = "CyberChef"
    category = ToolCategory.CRYPTO
    implementation = ImplementationMethod.PYTHON_NATIVE
    default_timeout = 30
    resource_profile = ResourceProfile(estimated_ram_mb=32, estimated_duration_s=5)

    def is_available(self) -> bool:
        return True  # pure Python fallback always available

    def build_command(self, target: str, **kwargs) -> list[str]:
        return []

    def run_native(self, target: str, **kwargs) -> tuple[str, str]:
        """Perform common encoding/decoding operations in pure Python."""
        import base64, hashlib, urllib.parse
        data = kwargs.get("data", target)
        operation = kwargs.get("operation", "detect")
        results = {}
        if operation == "detect" or operation == "all":
            # Try Base64 decode
            try:
                decoded = base64.b64decode(data, validate=True).decode("utf-8", errors="replace")
                results["base64_decoded"] = decoded
            except Exception:
                pass
            # URL decode
            results["url_decoded"] = urllib.parse.unquote(data)
            # Hashes
            for algo in ("md5", "sha1", "sha256"):
                results[f"{algo}_hash"] = hashlib.new(algo, data.encode()).hexdigest()
        elif operation == "base64_decode":
            results["decoded"] = base64.b64decode(data, validate=True).decode("utf-8", errors="replace")
        elif operation == "base64_encode":
            results["encoded"] = base64.b64encode(data.encode()).decode()
        elif operation == "url_decode":
            results["decoded"] = urllib.parse.unquote(data)
        elif operation == "hash":
            for algo in ("md5", "sha1", "sha256"):
                results[f"{algo}"] = hashlib.new(algo, data.encode()).hexdigest()
        return json.dumps(results, indent=2), ""

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        findings = []
        try:
            data = json.loads(stdout)
            if data.get("base64_decoded"):
                findings.append(ToolFinding(
                    tool=self.name,
                    title="Base64 decodering succesvol",
                    detail=f"Gedecodeerd: {data['base64_decoded'][:200]}",
                    severity=Severity.INFO,
                    recommendation="Controleer gedecodeerde data op gevoelige informatie.",
                ))
        except (json.JSONDecodeError, TypeError):
            pass
        return findings
