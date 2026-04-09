"""Tool Runner — central dispatcher with auto-discovery and parallel execution.

Discovers all tool wrappers via the ``@register`` decorator and provides
methods to run individual tools, tool sets, or full category scans.
"""

from __future__ import annotations

import concurrent.futures
import importlib
import logging
import pkgutil
from pathlib import Path
from typing import Generator

from tools.base import BaseToolWrapper, ToolCategory, ToolResult

logger = logging.getLogger("cyberpulse.tools.runner")

# ── Global Registry ────────────────────────────────────────────────
_TOOL_REGISTRY: dict[str, type[BaseToolWrapper]] = {}


def register(cls: type[BaseToolWrapper]) -> type[BaseToolWrapper]:
    """Class decorator to register a tool wrapper in the global registry."""
    if cls.name:
        _TOOL_REGISTRY[cls.name] = cls
        logger.debug("Registered tool: %s (%s)", cls.name, cls.display_name)
    return cls


def get_registry() -> dict[str, type[BaseToolWrapper]]:
    """Return the full tool registry (auto-discovers if empty)."""
    if not _TOOL_REGISTRY:
        _auto_discover()
    return dict(_TOOL_REGISTRY)


def _auto_discover():
    """Import all tool modules so their @register decorators fire."""
    tools_dir = Path(__file__).resolve().parent
    subdirs = [
        "password", "network", "web", "wireless", "sniffing",
        "osint", "exploitation", "postexploit", "forensics",
        "reversing", "vulnanalysis", "crypto",
    ]
    for subdir in subdirs:
        pkg_path = tools_dir / subdir
        if not pkg_path.is_dir():
            continue
        package_name = f"tools.{subdir}"
        try:
            pkg = importlib.import_module(package_name)
            for _importer, modname, _ispkg in pkgutil.iter_modules(pkg.__path__):
                try:
                    importlib.import_module(f"{package_name}.{modname}")
                except Exception as e:
                    logger.debug("Could not import %s.%s: %s", package_name, modname, e)
        except Exception as e:
            logger.debug("Could not import package %s: %s", package_name, e)


# ── Tool Runner ────────────────────────────────────────────────────

class ToolRunner:
    """Executes tools and yields SSE-compatible events."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.registry = get_registry()

    def get_available_tools(self) -> dict[str, dict]:
        """Return info about all registered tools and their availability."""
        result = {}
        for name, cls in self.registry.items():
            instance = cls(config=self.config)
            result[name] = {
                "name": name,
                "display_name": cls.display_name,
                "category": cls.category.value if isinstance(cls.category, ToolCategory) else cls.category,
                "available": instance.is_available(),
                "implementation": cls.implementation.value,
                "default_timeout": cls.default_timeout,
                "resource_profile": {
                    "estimated_ram_mb": cls.resource_profile.estimated_ram_mb,
                    "estimated_duration_s": cls.resource_profile.estimated_duration_s,
                    "requires_gpu": cls.resource_profile.requires_gpu,
                    "cpu_intensive": cls.resource_profile.cpu_intensive,
                },
            }
        return result

    def get_tools_by_category(self, category: ToolCategory) -> list[str]:
        """Return tool names in a specific category."""
        return [
            name for name, cls in self.registry.items()
            if cls.category == category
        ]

    def run_tool(self, tool_name: str, target: str,
                 output_dir: Path | None = None, **kwargs) -> ToolResult:
        """Run a single tool by name."""
        cls = self.registry.get(tool_name)
        if cls is None:
            return ToolResult(
                tool_name=tool_name,
                display_name=tool_name,
                category=ToolCategory.NETWORK_SCANNING,
                skipped=True,
                skip_reason=f"Tool '{tool_name}' niet gevonden in registry",
            )
        instance = cls(config=self.config)
        return instance.run(target, output_dir, **kwargs)

    def run_tools(self, tool_names: list[str], target: str,
                  output_dir: Path | None = None,
                  **kwargs) -> Generator[dict, None, list[ToolResult]]:
        """Run multiple tools sequentially, yielding SSE events.

        Yields event dicts and returns all ToolResults at the end.
        """
        results = []
        total = len(tool_names)

        yield {
            "type": "tools_start",
            "total_tools": total,
            "tools": tool_names,
        }

        for idx, name in enumerate(tool_names, 1):
            cls = self.registry.get(name)
            display = cls.display_name if cls else name

            yield {
                "type": "tool_start",
                "tool": name,
                "display_name": display,
                "index": idx,
                "total": total,
            }

            result = self.run_tool(name, target, output_dir, **kwargs)
            results.append(result)

            if result.skipped:
                yield {
                    "type": "tool_skipped",
                    "tool": name,
                    "display_name": display,
                    "skip_reason": result.skip_reason,
                    "index": idx,
                    "total": total,
                }
            elif result.success:
                yield {
                    "type": "tool_done",
                    "tool": name,
                    "display_name": display,
                    "findings_count": len(result.findings),
                    "duration": round(result.duration, 1),
                    "index": idx,
                    "total": total,
                }
            else:
                yield {
                    "type": "tool_error",
                    "tool": name,
                    "display_name": display,
                    "error": result.error,
                    "index": idx,
                    "total": total,
                }

        total_findings = sum(len(r.findings) for r in results)
        yield {
            "type": "tools_complete",
            "total_findings": total_findings,
            "tools_run": len(results),
            "tools_skipped": sum(1 for r in results if r.skipped),
        }

        return results

    def run_parallel(self, tool_names: list[str], target: str,
                     output_dir: Path | None = None,
                     max_workers: int = 3, **kwargs) -> list[ToolResult]:
        """Run multiple tools in parallel (no SSE events)."""
        results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.run_tool, name, target, output_dir, **kwargs): name
                for name in tool_names
            }
            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    results.append(future.result())
                except Exception as e:
                    logger.error("Parallel tool %s failed: %s", name, e)
                    results.append(ToolResult(
                        tool_name=name, display_name=name,
                        category=ToolCategory.NETWORK_SCANNING,
                        error=str(e),
                    ))
        return results


# ── Scan Profiles ──────────────────────────────────────────────────

TOOL_SCAN_PROFILES: dict[str, list[str]] = {
    "web_full": ["sqlmap", "nikto", "gobuster", "nuclei", "wpscan", "xsstrike", "commix", "arjun"],
    "web_quick": ["nikto", "gobuster", "nuclei"],
    "network_full": ["masscan", "netdiscover", "arpscan", "hping3", "tshark"],
    "network_quick": ["masscan", "tshark"],
    "recon_full": ["theharvester", "amass", "dnsrecon", "fierce", "spiderfoot"],
    "recon_quick": ["theharvester", "dnsrecon"],
    "password_audit": ["john", "hashcat", "hydra", "hashid"],
    "vuln_scan": ["nuclei", "lynis", "trivy", "grype"],
    "exploitation": ["searchsploit", "metasploit"],
    "forensics": ["volatility3", "binwalk", "exiftool", "strings_tool"],
    "crypto_audit": ["hashid", "hash_identifier", "stegseek"],
}


# ── Module Association Map ─────────────────────────────────────────

MODULE_TOOL_MAP: dict[str, list[str]] = {
    "01": ["masscan"],                             # Port scanning
    "02": [],                                       # Service enumeration
    "04": ["nuclei"],                               # Web vulnerabilities
    "05": ["sqlmap", "commix"],                     # Injection testing
    "06": ["hydra"],                                # Authentication
    "08": ["dnsrecon", "fierce"],                   # DNS recon
    "09": ["amass", "theharvester"],                # Subdomain enum
    "10": ["theharvester", "spiderfoot"],           # OSINT
    "11": [],                                       # Headers
    "12": ["nuclei", "nikto"],                      # Vuln scan
    "13": ["tshark"],                               # Network services
    "14": ["crackmapexec"],                         # SMB/LDAP
    "17": ["arjun"],                                # API testing
    "19": ["wpscan"],                               # CMS scanning
    "91": ["nuclei"],                               # Nuclei templates
    "92": ["gobuster"],                             # Dir fuzzing
    "93": ["sqlmap"],                               # SQLmap
}
