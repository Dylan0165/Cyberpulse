"""Celery tasks for scan orchestration."""

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
from app.services.scanner import (
    launch_scan_container,
    stop_scan_container,
    get_container_status,
    cleanup_stale_containers,
)
from app.workers.celery_app import celery_app
from app.schemas.scan import QUICK_PHASES, FULL_PHASES

logger = logging.getLogger(__name__)
settings = get_settings()

# Synchronous DB for Celery tasks
sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def get_redis_client():
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name="app.workers.scan_tasks.run_scan", bind=True, max_retries=2)
def run_scan(self, scan_id: str):
    """Execute a full scan — launches containers for each phase sequentially."""
    logger.info(f"Starting scan {scan_id}")

    with Session(sync_engine) as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return

        target = db.query(Target).filter(Target.id == scan.target_id).first()
        if not target:
            logger.error(f"Target {scan.target_id} not found")
            return

        # Verify target is still verified
        if not target.is_verified:
            scan.status = "failed"
            db.commit()
            logger.error(f"Target {target.id} is not verified")
            return

        # Determine phases
        if scan.scan_type == "quick":
            phases = QUICK_PHASES
        elif scan.scan_type == "full":
            phases = FULL_PHASES
        else:
            phases = scan.phases or QUICK_PHASES

        scan.status = "running"
        scan.started_at = datetime.now(timezone.utc)
        scan.phases = phases
        db.commit()

        # Build scan config
        scan_config = {
            "targets": [
                {
                    "type": target.target_type,
                    "value": target.value,
                }
            ],
            "scope": target.scope or {},
            "scan_type": scan.scan_type,
            "config": scan.config or {},
        }

        r = get_redis_client()
        total_phases = len(phases)

        for i, phase in enumerate(phases):
            scan.current_phase = phase
            scan.progress = int((i / total_phases) * 100)
            db.commit()

            # Publish progress via Redis
            r.publish(f"scan:{scan_id}:live", json.dumps({
                "type": "phase_start",
                "phase": phase,
                "progress": scan.progress,
                "timestamp": time.time(),
            }))

            try:
                container_id = launch_scan_container(
                    scan_id=str(scan.id),
                    scan_config=scan_config,
                    phase=phase,
                )
                scan.container_id = container_id
                db.commit()

                # Wait for container to complete
                _wait_for_container(container_id, timeout=settings.max_scan_duration_seconds // total_phases)

            except Exception as e:
                logger.error(f"Phase {phase} failed for scan {scan_id}: {e}")
                r.publish(f"scan:{scan_id}:live", json.dumps({
                    "type": "phase_error",
                    "phase": phase,
                    "error": str(e),
                    "timestamp": time.time(),
                }))
                continue

            r.publish(f"scan:{scan_id}:live", json.dumps({
                "type": "phase_complete",
                "phase": phase,
                "progress": int(((i + 1) / total_phases) * 100),
                "timestamp": time.time(),
            }))

        # Trigger AI analysis
        scan.status = "analyzing"
        scan.progress = 90
        db.commit()

        from app.workers.analysis_tasks import analyze_scan
        analyze_scan.delay(str(scan.id))


def _wait_for_container(container_id: str, timeout: int = 3600):
    """Poll container status until it exits or times out."""
    start = time.time()
    while time.time() - start < timeout:
        status = get_container_status(container_id)
        if status in ("exited", "removed"):
            return
        time.sleep(5)

    # Timeout — force stop
    stop_scan_container(container_id)
    logger.warning(f"Container {container_id[:12]} timed out after {timeout}s")


@celery_app.task(name="app.workers.scan_tasks.cleanup_containers")
def cleanup_containers():
    """Periodic task to clean up stale scanner containers."""
    removed = cleanup_stale_containers(max_age_seconds=settings.max_scan_duration_seconds)
    if removed:
        logger.info(f"Cleaned up {removed} stale containers")
