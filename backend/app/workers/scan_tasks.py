"""Celery tasks — 8-phase scan pipeline via the Kali VM scanner API."""

import json
import logging
import time
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
import app.models  # registers all models with SQLAlchemy before any query runs
from app.models.scan import Scan
from app.models.target import Target
from app.services.tool_runner import ToolRunner, ScannerUnavailableError
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


def _runner() -> ToolRunner:
    return ToolRunner(
        host=settings.kali_vm_host,
        port=settings.kali_vm_port,
        api_key=settings.scanner_api_key,
    )


def _pub(r: sync_redis.Redis, scan_id: str, event: dict):
    """Publish a live event and also append to the replay log."""
    payload = json.dumps(event)
    r.publish(f"scan:{scan_id}:live", payload)
    r.rpush(f"scan:{scan_id}:log", payload)
    r.expire(f"scan:{scan_id}:log", 86400)


# ── Phase definitions ─────────────────────────────────────────────────────────
# Each entry: (tool_name, args_template, timeout_seconds)
# {target} and {scan_id} are substituted at runtime.
# Credential placeholders: {username}, {password}, {bearer_token}

PHASES: list[tuple[str, list[tuple[str, str, int]]]] = [
    ("recon", [
        ("nmap",     "-sV -sC --open -p- {target}",                                    480),
        # PD httpx needs explicit http:// scheme; -u flag supported in recent versions
        ("httpx",    "-u http://{target} -title -tech-detect -status-code -silent",    120),
        ("whatweb",  "-a 3 {target}",                                                   60),
    ]),
    ("vuln_scan", [
        # -json deprecated in nuclei v3+; use -jsonl
        ("nuclei",   "-u {target} -severity critical,high,medium -jsonl -silent",      600),
    ]),
    ("webapp", [
        # nikto -Format json requires -output; omit Format flag to use plain text
        ("nikto",    "-h {target} -ask no",                                            300),
        ("sqlmap",   "-u {target} --batch --level=2 --risk=1 --forms",                600),
        ("ffuf",     "-u http://{target}/FUZZ -w /usr/share/wordlists/dirb/common.txt -mc 200,301,302,403 -ac -t 40", 180),
    ]),
    ("network", [
        ("nmap",     "--script=default,vuln -sV -p 21,22,23,25,53,80,110,139,143,443,445,3306,3389,5432,6379,8080,8443 {target}", 300),
    ]),
    ("auth", [
        # hydra — only runs when scan_mode != blackbox
        ("hydra",    "-L /usr/share/wordlists/metasploit/unix_users.txt -P /usr/share/wordlists/metasploit/unix_passwords.txt -t 4 {target} ssh", 300),
    ]),
    ("ssl", [
        ("testssl.sh", "--jsonfile /tmp/ssl_{scan_id}.json {target}",         180),
    ]),
    ("osint", [
        ("theharvester", "-d {target} -b all -l 100",                         180),
        ("gitleaks",     "detect --source /tmp --no-git --report-format json", 60),
    ]),
]

PHASE_NAMES    = [p[0] for p in PHASES]
PHASE_DISPLAY  = {
    "recon":    "Phase 1 — Reconnaissance",
    "vuln_scan":"Phase 2 — Vulnerability Scan",
    "webapp":   "Phase 3 — Web Application Tests",
    "network":  "Phase 4 — Network Services",
    "auth":     "Phase 5 — Authentication Tests",
    "ssl":      "Phase 6 — SSL/TLS Analysis",
    "osint":    "Phase 7 — OSINT & Secrets",
}


def _should_run_phase(phase_name: str, scan_mode: str, phases_enabled: list | None) -> bool:
    # Auth phase requires credentials
    if phase_name == "auth" and scan_mode == "blackbox":
        return False
    # If user specified custom phases, only run those
    if phases_enabled:
        return phase_name in phases_enabled
    return True


@celery_app.task(name="app.workers.scan_tasks.run_scan", bind=True, max_retries=2)
def run_scan(self, scan_id: str):
    """Full 8-phase scan orchestration via the Kali VM scanner API."""
    logger.info("Starting scan %s", scan_id)
    r = _redis()
    runner = _runner()

    with Session(sync_engine) as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return

        target_obj = db.query(Target).filter(Target.id == scan.target_id).first()
        if not target_obj:
            logger.error("Target for scan %s not found", scan_id)
            scan.status = "failed"
            db.commit()
            return

        target = target_obj.value

        # Pull scan context from config JSONB (set at scan creation)
        config      = scan.config or {}
        scan_mode   = config.get("scan_mode",    scan.scan_mode or "blackbox")
        credentials = config.get("credentials",  scan.credentials or {})
        phases_enabled = config.get("phases_enabled", scan.phases_enabled)

        # Persist resolved context to new dedicated columns
        scan.scan_mode   = scan_mode
        scan.credentials = credentials

        # Check Kali VM reachability
        if not runner.health_check():
            logger.error("Kali VM unreachable for scan %s", scan_id)
            _pub(r, scan_id, {"type": "error", "message": f"Kali VM ({settings.kali_vm_host}:{settings.kali_vm_port}) is not reachable. Make sure tool_api.py is running."})
            scan.status = "failed"
            db.commit()
            return

        scan.status     = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.phases_completed = []
        scan.tool_outputs     = {}
        db.commit()

        _pub(r, scan_id, {
            "type":    "scan_start",
            "target":  target,
            "mode":    scan_mode,
            "phases":  PHASE_NAMES,
            "timestamp": time.time(),
        })

        all_outputs: dict[str, dict[str, str]] = {}

        for phase_num, (phase_name, phase_tools) in enumerate(PHASES, start=1):
            if not _should_run_phase(phase_name, scan_mode, phases_enabled):
                _pub(r, scan_id, {
                    "type": "phase_skip", "phase": phase_name, "phase_num": phase_num,
                    "reason": "disabled by scan mode or user selection",
                })
                continue

            scan.current_phase     = phase_name
            scan.current_phase_num = phase_num
            scan.progress          = int(((phase_num - 1) / len(PHASES)) * 80)
            db.commit()

            _pub(r, scan_id, {
                "type": "phase_start", "phase": phase_name, "phase_num": phase_num,
                "display": PHASE_DISPLAY.get(phase_name, phase_name),
                "progress": scan.progress, "timestamp": time.time(),
            })

            phase_outputs: dict[str, str] = {}

            for tool_name, args_template, timeout in phase_tools:
                args = (
                    args_template
                    .replace("{target}", target)
                    .replace("{scan_id}", str(scan_id))
                    .replace("{username}", credentials.get("username", "admin"))
                    .replace("{password}", credentials.get("password", ""))
                    .replace("{bearer_token}", credentials.get("bearer_token", ""))
                )

                # For graybox: if credentials provided for hydra, use them
                if phase_name == "auth" and tool_name == "hydra" and credentials.get("username"):
                    args = (
                        f"-l {credentials['username']} "
                        f"-p {credentials.get('password','password')} "
                        f"-t 4 {target} ssh"
                    )

                logger.info(
                    "[%s] %s/%s → command: %s %s",
                    scan_id, phase_name, tool_name, tool_name, args[:300],
                )
                _pub(r, scan_id, {
                    "type": "tool_start", "phase": phase_name,
                    "tool": tool_name, "timestamp": time.time(),
                })

                result = runner.run_safe(tool_name, args, timeout)

                output = result.stdout or (f"[STDERR] {result.stderr}" if result.stderr else "")
                if not result.success and result.error:
                    output = f"[ERROR] {result.error}\n{output}"

                logger.info(
                    "[%s] %s/%s done — success=%s duration=%.1fs output_bytes=%d",
                    scan_id, phase_name, tool_name,
                    result.success, result.duration_s, len(output),
                )
                if output:
                    logger.info("[%s] %s/%s output[:1000]:\n%s",
                                scan_id, phase_name, tool_name, output[:1000])
                else:
                    logger.warning("[%s] %s/%s produced NO output (tool missing on Kali VM?)",
                                   scan_id, phase_name, tool_name)

                phase_outputs[tool_name] = output

                _pub(r, scan_id, {
                    "type":     "tool_done",
                    "phase":    phase_name,
                    "tool":     tool_name,
                    "success":  result.success,
                    "duration": result.duration_s,
                    "output":   output[:2000],
                    "timestamp": time.time(),
                })

            all_outputs[phase_name] = phase_outputs

            # Persist phase outputs incrementally
            current_tool_outputs = scan.tool_outputs or {}
            current_tool_outputs[phase_name] = phase_outputs
            scan.tool_outputs     = current_tool_outputs
            completed = list(scan.phases_completed or [])
            completed.append(phase_name)
            scan.phases_completed = completed
            db.commit()

            # Also write to Redis for the analysis task
            for tool_name, output in phase_outputs.items():
                if output:
                    r.setex(f"scan:{scan_id}:output:{phase_name}:{tool_name}", 7200, output)

            _pub(r, scan_id, {
                "type": "phase_complete", "phase": phase_name, "phase_num": phase_num,
                "progress": int((phase_num / len(PHASES)) * 80), "timestamp": time.time(),
            })

        # ── Summary before AI analysis ────────────────────────────────────────
        total_output_bytes = sum(
            len(out)
            for phase_data in all_outputs.values()
            for out in phase_data.values()
        )
        phases_with_output = [
            phase for phase, tools in all_outputs.items()
            if any(len(o) > 10 for o in tools.values())
        ]
        logger.info(
            "[%s] Scan phases complete — %d phases ran, %d had output, %d total bytes collected",
            scan_id, len(all_outputs), len(phases_with_output), total_output_bytes,
        )
        if total_output_bytes == 0:
            logger.warning(
                "[%s] ALL TOOLS RETURNED EMPTY OUTPUT — check Kali VM tools are installed "
                "and tool_api.py is running on %s:%s",
                scan_id, settings.kali_vm_host, settings.kali_vm_port,
            )

        # ── Phase 8: AI Analysis ──────────────────────────────────────────────
        scan.status   = "analyzing"
        scan.progress = 85
        db.commit()

        _pub(r, scan_id, {
            "type": "phase_start", "phase": "ai_analysis", "phase_num": 8,
            "display": "Phase 8 — AI Analysis (DeepSeek)",
            "progress": 85, "timestamp": time.time(),
        })

        from app.workers.analysis_tasks import analyze_scan
        analyze_scan.delay(str(scan.id))


@celery_app.task(name="app.workers.scan_tasks.cleanup_containers")
def cleanup_containers():
    """No-op — kept for scheduler compatibility."""
    pass
