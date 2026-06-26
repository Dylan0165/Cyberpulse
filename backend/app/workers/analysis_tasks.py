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
from app.models.notification import Notification
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
            # Resolve the scan owner's AI provider via the abstraction layer.
            provider_name = "deepseek"
            client = None
            model = None
            try:
                from app.models.user import User
                from app.services.ai_provider import AIProvider
                owner = db.query(User).filter(User.id == scan.user_id).first() if scan.user_id else None
                prov = AIProvider(owner)
                provider_name = prov.provider
                client, model = prov.get_client_and_model()
                logger.info("Scan %s using AI provider '%s'", scan_id, provider_name)
            except Exception as exc:
                logger.warning("AI provider resolution failed, using DeepSeek: %s", exc)
                client, model, provider_name = None, None, "deepseek"

            # Stream analysis output to the WebSocket channel
            report = analyze_scan_sync_streaming(
                scan_id=scan_id,
                target=target_obj.value,
                scan_type=scan.scan_type,
                phases_completed=list(all_outputs.keys()),
                all_outputs=all_outputs,
                redis_client=r,
                client=client,
                model=model,
            )
            try:
                scan.ai_provider_used = provider_name
            except Exception:
                pass

        # Deduplicate + enrich findings (OWASP/CWE/MITRE/CVE) and assign a stable
        # finding_id used by the finding-status table. Best-effort: never break
        # the analysis result on a post-processing error.
        try:
            from app.services.findings_deduplicator import FindingsDeduplicator, stable_finding_id
            from app.services.finding_mapper import FindingMapper
            raw = report.get("findings") or []
            deduped = FindingsDeduplicator.deduplicate(raw)
            for f in deduped:
                FindingMapper.enrich(f)
                f["id"] = stable_finding_id(scan_id, f)
            report["findings"] = deduped
            report["owasp_coverage"] = FindingMapper.owasp_coverage(deduped)
            report.pop("finding_counts", None)  # force recount from deduped set below
        except Exception as exc:  # noqa: BLE001
            logger.warning("findings dedup/enrich skipped for %s: %s", scan_id, exc)

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

        # Create an in-app notification for the scan owner (best-effort).
        # A notification failure must never break the analysis result.
        try:
            notif = Notification(
                user_id=scan.user_id,
                type="scan_complete",
                title="Scan voltooid",
                message=f"Scan van {target_obj.value} voltooid — {report.get('risk_score', 0)}/100",
                scan_id=scan.id,
                is_read=False,
            )
            db.add(notif)
            db.commit()
        except Exception as exc:
            logger.warning("Scan-complete notification skipped: %s", exc)

        # Best-effort HTML email, respecting the scan owner's notification prefs.
        # Falls back to NOTIFY_EMAIL when there is no owner. Email failures and a
        # missing SMTP config never affect the scan result.
        try:
            import os
            import asyncio as _aio
            from app.models.user import User as _User
            from app.services.email_service import email_service as _email

            owner = db.query(_User).filter(_User.id == scan.user_id).first() if scan.user_id else None
            to_addr = (owner.email if owner else None) or os.getenv("NOTIFY_EMAIL", "")
            if to_addr:
                crit = counts.get("critical", 0)
                scan_dict = {
                    "id": str(scan_id),
                    "target": target_obj.value,
                    "risk_score": report.get("risk_score", 0),
                    "findings_critical": crit,
                    "findings_high": counts.get("high", 0),
                }
                critical_only = bool(owner and getattr(owner, "notify_critical_only", False))
                want_complete = (owner is None) or getattr(owner, "notify_scan_complete", True)
                if critical_only:
                    if crit > 0:
                        crit_finding = next(
                            (f for f in (report.get("findings") or [])
                             if str(f.get("severity", "")).upper() == "CRITICAL"),
                            {},
                        )
                        _aio.run(_email.send_critical_finding(to_addr, scan_dict, crit_finding))
                elif want_complete:
                    _aio.run(_email.send_scan_complete(to_addr, scan_dict))
        except Exception as exc:
            logger.warning("Scan-complete email skipped: %s", exc)

        # Auto-generate the Secure Solution Report (best-effort — NEVER crash the
        # scan). Runs AFTER scan_complete is already published, so it does not
        # delay the completion event. Stored on a shared volume + path on the scan,
        # so the user's first download is instant (no AI call needed).
        try:
            from app.services.secure_solution import (
                fixable_findings, build_secure_solution, generate_secure_solution_pdf,
            )
            if fixable_findings(report):
                from app.models.user import User
                owner = (
                    db.query(User).filter(User.id == scan.user_id).first()
                    if scan.user_id else None
                )
                report_obj = build_secure_solution(scan, target_obj.value, report, owner)
                if report_obj.get("fixes"):
                    import os
                    pdf_bytes = generate_secure_solution_pdf(report_obj)
                    out_dir = os.getenv("SECURE_SOLUTION_DIR", "/opt/scanix/reports")
                    os.makedirs(out_dir, exist_ok=True)
                    pdf_path = os.path.join(out_dir, f"secure-solution-{scan.id}.pdf")
                    with open(pdf_path, "wb") as fh:
                        fh.write(pdf_bytes)
                    scan.secure_solution_path = pdf_path
                    db.commit()
                    logger.info("[%s] Secure Solution Rapport auto-generated: %s", scan_id, pdf_path)
        except Exception as exc:
            logger.error("[%s] Secure Solution generation failed: %s", scan_id, exc)
