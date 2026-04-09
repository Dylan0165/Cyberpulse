"""Base classes for all Kali tool wrappers.

Every tool wrapper inherits from ``BaseToolWrapper`` and produces
``ToolFinding`` objects that are fully compatible with the existing
CyberPulse ``scan_data.json`` finding schema.
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger("cyberpulse.tools.base")


# ── Enums ──────────────────────────────────────────────────────────

class Severity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class ToolCategory(str, Enum):
    PASSWORD_CRACKING = "password_cracking"
    NETWORK_SCANNING = "network_scanning"
    WEB_EXPLOITATION = "web_exploitation"
    WIRELESS = "wireless"
    SNIFFING = "sniffing"
    OSINT = "osint"
    EXPLOITATION = "exploitation"
    POST_EXPLOITATION = "post_exploitation"
    FORENSICS = "forensics"
    REVERSE_ENGINEERING = "reverse_engineering"
    VULN_ANALYSIS = "vuln_analysis"
    CRYPTO = "crypto"


class ImplementationMethod(str, Enum):
    SUBPROCESS = "subprocess"
    PYTHON_NATIVE = "python_native"
    API = "api"


# ── Data Classes ───────────────────────────────────────────────────

@dataclass
class ToolFinding:
    """Single finding from a tool — maps 1:1 to CyberPulse finding schema."""
    tool: str
    title: str
    detail: str
    severity: Severity = Severity.INFO
    description: str = ""
    recommendation: str = ""
    cve: str = ""
    port: int | None = None
    service: str = ""
    raw_output: str = ""
    references: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": f"tool_{self.tool}",
            "tool": self.tool,
            "title": self.title,
            "detail": self.detail,
            "severity": self.severity.value if isinstance(self.severity, Severity) else self.severity,
            "description": self.description,
            "recommendation": self.recommendation,
            "cve": self.cve,
            "port": self.port,
            "service": self.service,
            "raw_output": self.raw_output[:2000],
            "references": self.references,
        }


@dataclass
class ToolResult:
    """Result of running a single tool."""
    tool_name: str
    display_name: str
    category: ToolCategory
    success: bool = False
    skipped: bool = False
    skip_reason: str = ""
    error: str = ""
    findings: list[ToolFinding] = field(default_factory=list)
    raw_output: str = ""
    duration: float = 0.0

    def to_dict(self) -> dict:
        return {
            "tool_name": self.tool_name,
            "display_name": self.display_name,
            "category": self.category.value if isinstance(self.category, ToolCategory) else self.category,
            "success": self.success,
            "skipped": self.skipped,
            "skip_reason": self.skip_reason,
            "error": self.error,
            "findings": [f.to_dict() for f in self.findings],
            "raw_output": self.raw_output[:5000],
            "duration": round(self.duration, 2),
        }


# ── Resource Profile ───────────────────────────────────────────────

@dataclass
class ResourceProfile:
    """Expected resource usage for a tool."""
    estimated_ram_mb: int = 128
    estimated_duration_s: int = 120
    requires_gpu: bool = False
    cpu_intensive: bool = False


# ── Base Wrapper ───────────────────────────────────────────────────

class BaseToolWrapper:
    """Abstract base class for all Kali tool wrappers.

    Subclasses MUST implement:
        - ``build_command(target, **kwargs) -> list[str]``
        - ``parse(stdout, stderr, target, **kwargs) -> list[ToolFinding]``

    Optionally override:
        - ``run()`` for Python-native tools (no subprocess)
        - ``is_available()`` for custom availability checks
    """

    # ── Class attributes (override in subclass) ────────────────────
    name: str = ""
    display_name: str = ""
    category: ToolCategory = ToolCategory.NETWORK_SCANNING
    implementation: ImplementationMethod = ImplementationMethod.SUBPROCESS
    required_binaries: list[str] = []
    python_dependencies: list[str] = []
    default_timeout: int = 300
    resource_profile: ResourceProfile = ResourceProfile()

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self._laptop_mode = self.config.get("laptop_mode", True)

    # ── Public API ─────────────────────────────────────────────────

    def run(self, target: str, output_dir: Path | None = None, **kwargs) -> ToolResult:
        """Execute the tool and return structured results.

        This method handles all error cases — it NEVER raises.
        """
        result = ToolResult(
            tool_name=self.name,
            display_name=self.display_name,
            category=self.category,
        )

        t0 = time.time()

        try:
            # Check availability
            if not self.is_available():
                result.skipped = True
                result.skip_reason = self._get_skip_reason()
                result.success = True  # Not an error, just unavailable
                logger.info("Tool %s skipped: %s", self.name, result.skip_reason)
                result.duration = time.time() - t0
                return result

            # Build and execute command
            if self.implementation == ImplementationMethod.SUBPROCESS:
                result = self._run_subprocess(target, output_dir, result, **kwargs)
            elif self.implementation == ImplementationMethod.PYTHON_NATIVE:
                result = self._run_native(target, output_dir, result, **kwargs)
            elif self.implementation == ImplementationMethod.API:
                result = self._run_api(target, output_dir, result, **kwargs)

        except Exception as e:
            result.success = False
            result.error = str(e)
            logger.error("Tool %s crashed: %s", self.name, e, exc_info=True)

        result.duration = time.time() - t0
        return result

    def is_available(self) -> bool:
        """Check if the tool can execute on this system."""
        if self.implementation == ImplementationMethod.SUBPROCESS:
            return all(shutil.which(b) is not None for b in self.required_binaries)
        if self.implementation == ImplementationMethod.PYTHON_NATIVE:
            return self._check_python_deps()
        return True  # API tools are always "available" (key check at runtime)

    def build_command(self, target: str, **kwargs) -> list[str]:
        """Build the CLI command. Override in subclass."""
        raise NotImplementedError(f"{self.name} must implement build_command()")

    def parse(self, stdout: str, stderr: str, target: str, **kwargs) -> list[ToolFinding]:
        """Parse raw output into findings. Override in subclass."""
        raise NotImplementedError(f"{self.name} must implement parse()")

    def run_native(self, target: str, output_dir: Path | None = None, **kwargs) -> list[ToolFinding]:
        """Override for Python-native tools (ImplementationMethod.PYTHON_NATIVE)."""
        raise NotImplementedError(f"{self.name} must implement run_native()")

    # ── Internal Execution Methods ─────────────────────────────────

    def _run_subprocess(self, target: str, output_dir: Path | None,
                        result: ToolResult, **kwargs) -> ToolResult:
        """Execute via subprocess with timeout and error handling."""
        cmd = self.build_command(target, **kwargs)
        if not cmd:
            result.skipped = True
            result.skip_reason = "Geen commando gegenereerd"
            return result

        timeout = kwargs.get("timeout", self.default_timeout)
        if self._laptop_mode:
            timeout = min(timeout, 600)  # Cap at 10 min in laptop mode

        logger.info("Running: %s (timeout=%ds)", " ".join(cmd[:3]) + "...", timeout)

        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            result.raw_output = (proc.stdout or "") + "\n" + (proc.stderr or "")
            result.findings = self.parse(proc.stdout or "", proc.stderr or "", target, **kwargs)
            result.success = True

        except subprocess.TimeoutExpired:
            result.success = False
            result.error = f"Timeout na {timeout}s"
            logger.warning("Tool %s timed out after %ds", self.name, timeout)

        except FileNotFoundError:
            result.skipped = True
            result.skip_reason = f"Binary niet gevonden: {cmd[0]}"

        return result

    def _run_native(self, target: str, output_dir: Path | None,
                    result: ToolResult, **kwargs) -> ToolResult:
        """Execute a Python-native tool."""
        result.findings = self.run_native(target, output_dir, **kwargs)
        result.success = True
        return result

    def _run_api(self, target: str, output_dir: Path | None,
                 result: ToolResult, **kwargs) -> ToolResult:
        """Execute an API-based tool."""
        result.findings = self.run_native(target, output_dir, **kwargs)
        result.success = True
        return result

    # ── Helpers ─────────────────────────────────────────────────────

    def _check_python_deps(self) -> bool:
        """Check if required Python packages are importable."""
        for dep in self.python_dependencies:
            try:
                __import__(dep.replace("-", "_"))
            except ImportError:
                return False
        return True

    def _get_skip_reason(self) -> str:
        """Generate a human-readable skip reason."""
        if self.implementation == ImplementationMethod.SUBPROCESS:
            missing = [b for b in self.required_binaries if shutil.which(b) is None]
            return f"Ontbrekende binaries: {', '.join(missing)}"
        if self.implementation == ImplementationMethod.PYTHON_NATIVE:
            missing = []
            for dep in self.python_dependencies:
                try:
                    __import__(dep.replace("-", "_"))
                except ImportError:
                    missing.append(dep)
            return f"Ontbrekende Python packages: {', '.join(missing)}"
        return "Tool niet beschikbaar"

    def _get_timeout(self, **kwargs) -> int:
        """Get effective timeout respecting laptop mode."""
        timeout = kwargs.get("timeout", self.default_timeout)
        if self._laptop_mode:
            timeout = min(timeout, 600)
        return timeout
