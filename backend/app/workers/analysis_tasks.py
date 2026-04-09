"""Celery tasks for AI analysis of scan results."""

import json
import logging
from datetime import datetime, timezone

import redis as sync_redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import anthropic

from app.core.config import get_settings
from app.models.scan import Scan
from app.models.target import Target
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)
settings = get_settings()

sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def get_redis_client():
    return sync_redis.from_url(settings.redis_url, decode_responses=True)


SYSTEM_PROMPT = """You are an expert penetration tester with OSCP, CISSP, and CEH certifications.
Analyze the provided scan output and produce a structured security report.

For each finding, provide:
- CVE IDs where applicable
- CVSS v3.1 score (calculate if not present)
- Risk level: CRITICAL / HIGH / MEDIUM / LOW / INFO
- Business impact (plain English, no jargon)
- Proof of concept description (no actual exploit code)
- Remediation steps (specific, actionable, with code examples where helpful)
- OWASP category if applicable
- Estimated fix time

At the end, provide:
- Executive summary (for non-technical CEO/CFO audience, max 3 paragraphs)
- Technical summary (for IT team)
- Prioritized remediation roadmap (Quick wins < 1 day, Short term < 1 week, Long term < 1 month)
- Overall security score 0-100 with breakdown per category

Return ONLY valid JSON. Never include actual working exploit code."""


@celery_app.task(name="app.workers.analysis_tasks.analyze_scan", bind=True, max_retries=2)
def analyze_scan(self, scan_id: str):
    """Collect all phase outputs from Redis and send to Claude for analysis."""
    logger.info(f"Starting AI analysis for scan {scan_id}")

    r = get_redis_client()

    with Session(sync_engine) as db:
        scan = db.query(Scan).filter(Scan.id == scan_id).first()
        if not scan:
            logger.error(f"Scan {scan_id} not found")
            return

        target = db.query(Target).filter(Target.id == scan.target_id).first()
        if not target:
            logger.error(f"Target for scan {scan_id} not found")
            return

        # Collect all tool outputs from Redis
        all_outputs = {}
        phases = scan.phases or []
        for phase in phases:
            pattern = f"scan:{scan_id}:output:{phase}:*"
            keys = r.keys(pattern)
            phase_outputs = {}
            for key in keys:
                tool_name = key.split(":")[-1]
                output = r.get(key)
                if output:
                    phase_outputs[tool_name] = output
            if phase_outputs:
                all_outputs[phase] = phase_outputs

        if not all_outputs:
            logger.warning(f"No scan outputs found for {scan_id}")
            scan.status = "completed"
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)
            scan.security_score = 100.0
            db.commit()
            return

        # Build the prompt
        sections = []
        for phase, tools in all_outputs.items():
            sections.append(f"\n{'='*60}\nPHASE: {phase.upper()}\n{'='*60}")
            for tool_name, output in tools.items():
                truncated = output[:30000] if len(output) > 30000 else output
                sections.append(f"\n--- {tool_name} ---\n{truncated}")

        user_message = f"""Analyze the following penetration test results.

Target: {target.value}
Scan Type: {scan.scan_type}
Scan ID: {scan_id}
Phases completed: {json.dumps(phases)}

--- FULL SCAN OUTPUT ---
{"\\n".join(sections)}
--- END SCAN OUTPUT ---

Produce the comprehensive structured JSON security report."""

        # Call Claude (synchronous for Celery)
        client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

        try:
            response = client.messages.create(
                model=settings.claude_model,
                max_tokens=32000,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_message}],
            )

            raw_response = response.content[0].text

            # Publish to Redis for live streaming
            r.publish(f"scan:{scan_id}:live", json.dumps({
                "type": "analysis_complete",
                "timestamp": __import__("time").time(),
            }))

            # Parse the JSON report
            report_data = _parse_report(raw_response)

            # Update scan record
            scan.status = "completed"
            scan.progress = 100
            scan.completed_at = datetime.now(timezone.utc)

            if report_data:
                scan.security_score = report_data.get("overall_score", 0)
                scan.critical_count = report_data.get("critical_count", 0)
                scan.high_count = report_data.get("high_count", 0)
                scan.medium_count = report_data.get("medium_count", 0)
                scan.low_count = report_data.get("low_count", 0)
                scan.info_count = report_data.get("info_count", 0)

                # Only persist report if user opted in
                if scan.save_report:
                    scan.report_data = report_data
                else:
                    # Store temporarily in Redis (1 hour TTL) for UI display
                    r.setex(
                        f"scan:{scan_id}:report",
                        3600,
                        json.dumps(report_data),
                    )

            db.commit()
            logger.info(f"AI analysis complete for scan {scan_id}")

        except Exception as e:
            logger.error(f"AI analysis failed for {scan_id}: {e}")
            scan.status = "failed"
            db.commit()
            raise self.retry(exc=e, countdown=60)


def _parse_report(raw: str) -> dict | None:
    """Parse Claude's JSON output."""
    try:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            lines = cleaned.split("\n")
            cleaned = "\n".join(lines[1:])
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
        return json.loads(cleaned)
    except (json.JSONDecodeError, Exception) as e:
        logger.error(f"Failed to parse report JSON: {e}")
        return None
