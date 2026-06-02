"""Celery tasks for scan orchestration via the Kali VM scanner."""

import json
import logging
import time
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.scan import Scan
from app.models.target import Target
from app.services.scanner import run_phase, stop_scan_container
from app.workers.celery_app import celery_app
from app.schemas.scan import QUICK_PHASES, FULL_PHASES

logger = logging.getLogger(__name__)
settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def get_redis_client() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name="app.workers.scan_tasks.run_scan", bind=True, max_retries=2)
def run_scan(self, scan_id: str):
    """
    Execute a full scan.

    For each phase, calls run_phase() which sends tool jobs to the Kali VM
    and stores stdout in Redis under scan:{id}:output:{phase}:{tool}.
    After all phases complete, triggers AI analysis.
    """
    logger.info("Starting scan %s", scan_id)

    with Session(sync_engine) as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error("Scan %s not found", scan_id)
            return

        target = db.query(Target).filter(Target.id == scan.target_id).first()
        if not target:
            logger.error("Target for scan %s not found", scan_id)
            scan.status = "failed"
            db.commit()
            return

        if not target.is_verified:
            logger.error("Target %s is not verified", target.id)
            scan.status = "failed"
            db.commit()
            return

        phases = (
            QUICK_PHASES if scan.scan_type == "quick"
            else FULL_PHASES if scan.scan_type == "full"
            else scan.phases or QUICK_PHASES
        )

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.phases = phases
        db.commit()

        r = get_redis_client()
        total = len(phases)

        for i, phase in enumerate(phases):
            scan.current_phase = phase
            scan.progress = int((i / total) * 100)
            db.commit()

            r.publish(f"scan:{scan_id}:live", json.dumps({
                "type": "phase_start",
                "phase": phase,
                "progress": scan.progress,
                "timestamp": time.time(),
            }))

            try:
                outputs = run_phase(
                    phase=phase,
                    target=target.value,
                    scan_id=str(scan.id),
                )
                tool_count = len(outputs)
            except Exception as exc:
                logger.error("Phase %s failed for scan %s: %s", phase, scan_id, exc)
                r.publish(f"scan:{scan_id}:live", json.dumps({
                    "type": "phase_error",
                    "phase": phase,
                    "error": str(exc),
                    "timestamp": time.time(),
                }))
                tool_count = 0

            r.publish(f"scan:{scan_id}:live", json.dumps({
                "type": "phase_complete",
                "phase": phase,
                "tools_run": tool_count,
                "progress": int(((i + 1) / total) * 100),
                "timestamp": time.time(),
            }))

        # Hand off to AI analysis
        scan.status = "analyzing"
        scan.progress = 90
        db.commit()

        from app.workers.analysis_tasks import analyze_scan
        analyze_scan.delay(str(scan.id))


@celery_app.task(name="app.workers.scan_tasks.cleanup_containers")
def cleanup_containers():
    """No-op periodic task — kept for scheduler compatibility."""
    logger.debug("cleanup_containers: no Docker containers in use")
