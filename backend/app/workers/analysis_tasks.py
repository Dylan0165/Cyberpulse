"""Celery task — DeepSeek AI analysis of completed scan output."""

import json
import logging
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
import app.models  # registers all models with SQLAlchemy before any query runs
from app.models.scan import Scan
from app.models.target import Target
from app.services.ai_analysis import analyze_scan_sync_streaming
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _redis() -> sync_redis.Redis:
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


@celery_app.task(name="app.workers.analysis_tasks.analyze_scan", bind=True, max_retries=2)
def analyze_scan(self, scan_id: str):
    """
    Collect all tool outputs from Redis + scan.tool_outputs,
    send to DeepSeek for analysis, persist the structured report.
    """
    logger.info("Starting AI analysis for scan %s", scan_id)
    r = _redis()

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

        # Collect tool outputs: prefer the JSONB column, fall back to Redis keys
        all_outputs: dict[str, dict[str, str]] = {}

        if scan.tool_outputs:
            all_outputs = scan.tool_outputs
        else:
            # Redis fallback
            phases_done = scan.phases_completed or []
            for phase in phases_done:
                pattern = f"scan:{scan_id}:output:{phase}:*"
                keys = r.keys(pattern)
                phase_data: dict[str, str] = {}
                for key in keys:
                    tool_name = key.split(":")[-1]
                    val = r.get(key)
                    if val:
                        phase_data[tool_name] = val
                if phase_data:
                    all_outputs[phase] = phase_data

        if not all_outputs:
            logger.warning("No tool outputs found for scan %s — generating empty report", scan_id)
            report = {
                "scan_id": scan_id,
                "target": target_obj.value,
                "scan_type": scan.scan_type,
                "risk_score": 100,
                "risk_level": "INFO",
                "management_summary": "No scan output available. The scan may have been blocked by the target or all tools were skipped.",
                "technical_summary": "No tool output collected.",
                "findings": [],
                "finding_counts": {"critical":0,"high":0,"medium":0,"low":0,"info":0},
                "remediation_roadmap": {"quick_wins":[],"short_term":[],"long_term":[]},
                "compliance_mapping": {"owasp_top10":[],"iso27001":[],"nis2":[]},
            }
        else:
            # Stream DeepSeek output to the analysis WebSocket channel
            report = analyze_scan_sync_streaming(
                scan_id=scan_id,
                target=target_obj.value,
                scan_type=scan.scan_type,
                phases_completed=list(all_outputs.keys()),
                all_outputs=all_outputs,
                redis_client=r,
            )

        # Extract finding counts from report
        counts = report.get("finding_counts") or {}
        if not counts and report.get("findings"):
            # Count from findings list if finding_counts not present
            for f in report["findings"]:
                sev = (f.get("severity") or "info").lower()
                counts[sev] = counts.get(sev, 0) + 1

        # Persist to scan record
        scan.ai_analysis     = report
        scan.report_data     = report
        scan.status          = "completed"
        scan.progress        = 100
        scan.completed_at    = datetime.now(timezone.utc)
        scan.security_score  = float(100 - report.get("risk_score", 0))
        scan.critical_count  = counts.get("critical", 0)
        scan.high_count      = counts.get("high", 0)
        scan.medium_count    = counts.get("medium", 0)
        scan.low_count       = counts.get("low", 0)
        scan.info_count      = counts.get("info", 0)

        # Store findings in dedicated column too
        scan.findings = report.get("findings", [])

        # Store in Redis for 1 hour (for UI without DB persistence)
        r.setex(f"scan:{scan_id}:report", 3600, json.dumps(report))

        db.commit()

        # Notify frontend: analysis done
        r.publish(f"scan:{scan_id}:live", json.dumps({
            "type":        "scan_complete",
            "risk_score":  report.get("risk_score", 0),
            "risk_level":  report.get("risk_level", "LOW"),
            "findings":    len(report.get("findings", [])),
            "critical":    counts.get("critical", 0),
            "high":        counts.get("high", 0),
            "timestamp":   __import__("time").time(),
        }))

        logger.info(
            "Analysis complete for scan %s: risk=%s score=%s findings=%s",
            scan_id, report.get("risk_level"), report.get("risk_score"),
            len(report.get("findings", [])),
        )
