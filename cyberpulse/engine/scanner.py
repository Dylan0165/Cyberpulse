"""Scan orchestrator — runs modules sequentially, yields SSE-friendly events."""

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from config import Config
from engine.module_runner import run_module

logger = logging.getLogger("cyberpulse.engine.scanner")


class Scanner:
    """Orchestrates a penetration test by running selected modules in order."""

    def __init__(self, target: str, modules: list[str], scan_type: str = "quick",
                 scan_mode: str = "blackbox", credentials: dict | None = None,
                 target_type: str = "web"):
        self.target = target
        self.modules = sorted(modules)
        self.scan_type = scan_type
        self.scan_mode = scan_mode
        self.target_type = target_type
        self.credentials = credentials or {}
        self.scan_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
        self.scan_dir = Config.SCANS_DIR / self.scan_id
        self.scan_dir.mkdir(parents=True, exist_ok=True)

    def run(self):
        """Generator that yields event dicts as the scan progresses.

        Event types:
            scan_start      — scan begins
            module_start    — about to run module
            module_done     — module finished successfully
            module_error    — module failed
            log             — informational message
            scan_complete   — all modules finished
        """
        total = len(self.modules)
        all_results = []

        yield {
            "type": "scan_start",
            "scan_id": self.scan_id,
            "target": self.target,
            "scan_type": self.scan_type,
            "scan_mode": self.scan_mode,
            "total_modules": total,
        }

        for idx, mod_id in enumerate(self.modules, 1):
            info = Config.MODULE_INFO.get(mod_id, {})
            name = info.get("name", f"Module {mod_id}")

            yield {
                "type": "module_start",
                "module": mod_id,
                "name": name,
                "index": idx,
                "total": total,
            }

            result = run_module(mod_id, self.target, self.scan_dir,
                                config={
                                    "credentials": self.credentials,
                                    "scan_mode": self.scan_mode,
                                    "target_type": self.target_type,
                                })
            all_results.append(result.to_dict())

            if result.skipped:
                yield {
                    "type": "module_done",
                    "module": mod_id,
                    "name": name,
                    "findings_count": 0,
                    "duration": round(result.duration, 1),
                    "index": idx,
                    "total": total,
                    "skipped": True,
                }
            elif result.success:
                yield {
                    "type": "module_done",
                    "module": mod_id,
                    "name": name,
                    "findings_count": len(result.findings),
                    "duration": round(result.duration, 1),
                    "index": idx,
                    "total": total,
                }
            else:
                yield {
                    "type": "module_error",
                    "module": mod_id,
                    "name": name,
                    "error": result.error or "Unknown error",
                    "index": idx,
                    "total": total,
                }

        # Run exploit correlator BEFORE AI analysis
        try:
            from engine.exploit_correlator import ExploitCorrelator
            correlator = ExploitCorrelator(self.scan_dir, config={})
            all_results = correlator.correlate(all_results)
            yield {"type": "log", "message": "Exploit correlatie voltooid"}
        except Exception as e:
            logger.warning("Exploit correlation failed: %s", e)
            yield {"type": "log", "message": f"Exploit correlatie overgeslagen: {e}"}

        # Save scan data
        scan_data = {
            "scan_id": self.scan_id,
            "target": self.target,
            "scan_type": self.scan_type,
            "scan_mode": self.scan_mode,
            "target_type": self.target_type,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "modules_run": self.modules,
            "results": all_results,
            "total_findings": sum(len(r["findings"]) for r in all_results),
        }

        data_path = self.scan_dir / "scan_data.json"
        with open(data_path, "w", encoding="utf-8") as f:
            json.dump(scan_data, f, indent=2, ensure_ascii=False, default=str)

        logger.info(
            "Scan %s complete — %d modules, %d total findings",
            self.scan_id, total, scan_data["total_findings"],
        )

        yield {
            "type": "scan_complete",
            "scan_id": self.scan_id,
            "total_findings": scan_data["total_findings"],
            "report_path": str(data_path),
        }
