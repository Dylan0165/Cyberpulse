"""
Kali Proxy — stuurt tool-opdrachten door naar de Kali VM (192.168.121.28:5001)
als de binary niet lokaal beschikbaar is in de cyberpulse-web container.

Gebruik:
    Stel KALI_API_URL in via .env:
        KALI_API_URL=http://192.168.121.28:5001

    De BaseToolWrapper roept automatisch de proxy aan als de binary
    niet lokaal gevonden wordt maar KALI_API_URL wél ingesteld is.
"""

import logging
import os
import shutil
from pathlib import Path

import requests

from tools.base import BaseToolWrapper, ToolResult, ToolFinding, Severity

logger = logging.getLogger("cyberpulse.tools.kali_proxy")

# URL van de Kali VM tool API — instelbaar via .env
KALI_API_URL = os.getenv("KALI_API_URL", "http://192.168.121.28:5001")


def is_kali_available() -> bool:
    """Check of de Kali VM tool API bereikbaar is."""
    try:
        resp = requests.get(f"{KALI_API_URL}/health", timeout=3)
        return resp.ok
    except Exception:
        return False


def run_on_kali(tool_name: str, target: str, args: list[str],
                timeout: int = 300) -> dict:
    """
    Voer een tool uit op de Kali VM.

    Returns:
        {
            "success":    bool,
            "stdout":     str,
            "stderr":     str,
            "returncode": int,
        }
    """
    try:
        resp = requests.post(
            f"{KALI_API_URL}/run",
            json={"tool": tool_name, "target": target, "args": args},
            timeout=timeout + 10,  # iets meer dan de tool timeout
        )
        if resp.ok:
            return resp.json()
        return {"success": False, "error": f"Kali API fout: {resp.status_code}", "stdout": "", "stderr": ""}
    except requests.Timeout:
        return {"success": False, "error": f"Kali API timeout na {timeout}s", "stdout": "", "stderr": ""}
    except requests.ConnectionError:
        return {"success": False, "error": "Kali VM niet bereikbaar", "stdout": "", "stderr": ""}
    except Exception as e:
        return {"success": False, "error": str(e), "stdout": "", "stderr": ""}


class KaliProxyMixin(BaseToolWrapper):
    """
    Mixin die automatisch de Kali VM gebruikt als fallback
    wanneer een binary niet lokaal beschikbaar is.

    Gebruik:
        class NmapWrapper(KaliProxyMixin, BaseToolWrapper):
            name = "nmap"
            required_binaries = ["nmap"]
            ...
    """

    def is_available(self) -> bool:
        # Eerst lokaal checken
        if super().is_available():
            return True
        # Dan checken of Kali beschikbaar is
        if KALI_API_URL and is_kali_available():
            logger.debug("Tool %s niet lokaal — gebruik Kali VM (%s)", self.name, KALI_API_URL)
            return True
        return False

    def _run_subprocess(self, target: str, output_dir: Path | None,
                        result: ToolResult, **kwargs) -> ToolResult:
        # Als binary lokaal beschikbaar is: gebruik lokale uitvoering
        if all(shutil.which(b) for b in self.required_binaries):
            return super()._run_subprocess(target, output_dir, result, **kwargs)

        # Anders: stuur door naar Kali VM
        logger.info("Tool %s → Kali VM %s (target=%s)", self.name, KALI_API_URL, target)

        cmd = self.build_command(target, **kwargs)
        # Verwijder de binary zelf (cmd[0]) — de Kali API voegt die toe
        args = cmd[1:] if cmd else []
        timeout = kwargs.get("timeout", self.default_timeout)

        response = run_on_kali(self.name, target, args, timeout=timeout)

        if "error" in response and not response.get("success"):
            if "niet bereikbaar" in response["error"] or "niet gevonden" in response["error"]:
                result.skipped = True
                result.skip_reason = response["error"]
            else:
                result.success = False
                result.error = response["error"]
            return result

        stdout = response.get("stdout", "")
        stderr = response.get("stderr", "")
        result.raw_output = stdout + ("\n" + stderr if stderr else "")
        result.findings = self.parse(stdout, stderr, target, **kwargs)
        result.success = True
        return result
