"""Module runner — executes individual scan modules.

Includes target-type filtering, scope validation, and
associated Kali tool execution via the tools subsystem.
"""

import importlib
import logging
import time
import traceback
from pathlib import Path

logger = logging.getLogger("cyberpulse.engine.runner")


class ModuleResult:
    """Structured result from a single module execution."""

    __slots__ = ("module_id", "name", "phase", "success", "findings", "raw_output", "error", "duration", "skipped")

    def __init__(self, module_id: str, name: str, phase: str):
        self.module_id = module_id
        self.name = name
        self.phase = phase
        self.success = False
        self.findings = []
        self.raw_output = ""
        self.error = None
        self.duration = 0.0
        self.skipped = False

    def to_dict(self) -> dict:
        return {
            "module_id": self.module_id,
            "name": self.name,
            "phase": self.phase,
            "success": self.success,
            "findings": self.findings,
            "raw_output": self.raw_output,
            "error": self.error,
            "duration": round(self.duration, 2),
            "skipped": self.skipped,
        }


def run_module(module_id: str, target: str, scan_dir, config: dict | None = None) -> ModuleResult:
    """Import and execute a single scan module.

    Each module lives at ``modules/m{module_id}.py`` and must expose a
    ``Scanner`` class with ``__init__(target, output_dir, config)`` and a
    ``run()`` method returning ``{"findings": [...], "raw_output": "..."}``.

    If the module defines ``target_types`` and the current scan's ``target_type``
    is not in that list, the module is skipped automatically.
    """
    from config import Config

    config = config or {}
    info = Config.MODULE_INFO.get(module_id, {})
    name = info.get("name", f"Module {module_id}")
    phase = info.get("phase", "unknown")
    result = ModuleResult(module_id, name, phase)

    t0 = time.time()
    try:
        mod = importlib.import_module(f"modules.m{module_id}")
        scanner_class = getattr(mod, "Scanner", None)
        if scanner_class is None:
            raise AttributeError(f"modules.m{module_id} has no Scanner class")

        # Target-type filtering: skip module if target_type doesn't match
        target_type = config.get("target_type", "web")
        module_target_types = getattr(scanner_class, "target_types", None)
        if module_target_types and target_type not in module_target_types:
            result.skipped = True
            result.success = True
            result.raw_output = f"Overgeslagen: module ondersteunt {module_target_types}, scan type is {target_type}"
            logger.info("Module %s (%s) skipped — target_type %s not in %s", module_id, name, target_type, module_target_types)
            result.duration = time.time() - t0
            return result

        # Scope validation
        try:
            from engine.scope_validator import ScopeValidator
            validator = ScopeValidator(target, config)
            if not validator.validate(target):
                result.skipped = True
                result.success = False
                result.error = "Target buiten scope"
                result.raw_output = f"Scope violation: {validator.get_violations()}"
                logger.warning("Module %s blocked by scope validator", module_id)
                result.duration = time.time() - t0
                return result
        except ImportError:
            pass  # Scope validator not available, continue

        instance = scanner_class(target=target, output_dir=scan_dir, config=config)

        # Optional per-module request delay (throttling)
        request_delay_ms = config.get("request_delay_ms", 0)
        if request_delay_ms > 0:
            time.sleep(request_delay_ms / 1000.0)

        # Run module with exponential backoff on HTTP 429
        _backoff_times = [1, 2, 4]
        output = None
        for _attempt in range(len(_backoff_times) + 1):
            try:
                output = instance.run()
                break
            except Exception as exc:
                exc_str = str(exc).lower()
                is_rate_limited = (
                    "429" in exc_str
                    or "rate limit" in exc_str
                    or "too many requests" in exc_str
                )
                if is_rate_limited and _attempt < len(_backoff_times):
                    wait = _backoff_times[_attempt]
                    logger.warning(
                        "Module %s (%s) rate-limited (attempt %d/%d), "
                        "retrying in %ds",
                        module_id, name, _attempt + 1, len(_backoff_times), wait,
                    )
                    time.sleep(wait)
                    continue
                raise  # re-raise non-429 errors or exhausted retries

        result.success = True
        result.findings = output.get("findings", [])
        result.raw_output = output.get("raw_output", "")
        logger.info("Module %s (%s) done — %d findings", module_id, name, len(result.findings))

    except Exception as e:
        result.success = False
        result.error = str(e)
        result.raw_output = traceback.format_exc()
        logger.error("Module %s (%s) failed: %s", module_id, name, e)

    result.duration = time.time() - t0
    return result


# ── Associated Tool Execution ──────────────────────────────────────

def run_associated_tools(module_id: str, target: str, scan_dir: Path,
                         config: dict | None = None) -> list[dict]:
    """Run Kali tools associated with a module via MODULE_TOOL_MAP.

    Returns a list of serialised ToolResult dicts that can be merged into
    the module's scan_data output.
    """
    try:
        from tools.tool_runner import ToolRunner, MODULE_TOOL_MAP
    except ImportError:
        logger.debug("tools subsystem not installed — skipping associated tools")
        return []

    tool_names = MODULE_TOOL_MAP.get(module_id, [])
    if not tool_names:
        return []

    runner = ToolRunner(config=config)
    results = []
    for name in tool_names:
        try:
            result = runner.run_tool(name, target, scan_dir)
            results.append(result.to_dict())
        except Exception as e:
            logger.error("Associated tool %s failed for module %s: %s", name, module_id, e)
    return results
