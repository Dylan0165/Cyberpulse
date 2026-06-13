"""Dashboard statistics endpoint — per-account isolated."""

import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_optional_user
from app.models.scan import Scan
from app.models.user import User

router = APIRouter()

_STUDENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def _risk_for_scan(scan: Scan) -> int:
    """Compute a 0-100 risk score for a single scan."""
    if scan.security_score is not None:
        return round(100 - scan.security_score)
    risk = (
        (scan.critical_count or 0) * 25
        + (scan.high_count or 0) * 12
        + (scan.medium_count or 0) * 5
    )
    return min(risk, 100)


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    auth_user: User | None = Depends(get_optional_user),
):
    try:
        owner = auth_user.id if auth_user is not None else _STUDENT_USER_ID
        result = await db.execute(select(Scan).where(Scan.user_id == owner))
        scans = result.scalars().all()

        total_scans = len(scans)
        active_targets = len({s.target_id for s in scans})

        completed = [s for s in scans if s.status == "completed"]
        critical_open = sum((s.critical_count or 0) for s in completed)

        # avg_risk_score: average risk over completed scans in the last 30 days
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        recent = []
        for s in completed:
            created = s.created_at
            if created is None:
                continue
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            if created >= cutoff:
                recent.append(s)
        if recent:
            avg_risk_score = round(
                sum(_risk_for_scan(s) for s in recent) / len(recent)
            )
        else:
            avg_risk_score = 0

        # risk_trend: last 10 completed scans ordered by created_at asc
        completed_sorted = sorted(
            (s for s in completed if s.created_at is not None),
            key=lambda s: s.created_at,
        )
        last_ten = completed_sorted[-10:]
        risk_trend = [
            {
                "date": s.created_at.strftime("%Y-%m-%d"),
                "score": _risk_for_scan(s),
            }
            for s in last_ten
        ]

        return {
            "total_scans": total_scans,
            "active_targets": active_targets,
            "critical_open": critical_open,
            "avg_risk_score": avg_risk_score,
            "risk_trend": risk_trend,
        }
    except Exception:
        return {
            "total_scans": 0,
            "active_targets": 0,
            "critical_open": 0,
            "avg_risk_score": 0,
            "risk_trend": [],
        }
