"""Scheduled-scan endpoints — manage recurring automated scans.

Login required. Celery Beat (run_scheduled_scans) picks up active schedules whose
next_run_at has passed.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.scheduled_scan import ScheduledScan
from app.models.user import User

router = APIRouter(prefix="/schedule", tags=["schedule"])

_INTERVALS = {
    "daily": timedelta(days=1),
    "weekly": timedelta(days=7),
    "monthly": timedelta(days=30),
}


class ScheduleCreate(BaseModel):
    target_ip: str
    target_name: Optional[str] = None
    schedule_type: str = "weekly"
    phases: Optional[list] = None
    custom_modules: Optional[list] = None


def _interval(schedule_type: str) -> timedelta:
    return _INTERVALS.get(schedule_type, _INTERVALS["weekly"])


def _serialize(s: ScheduledScan) -> dict:
    return {
        "id": str(s.id),
        "user_id": str(s.user_id) if s.user_id else None,
        "target_ip": s.target_ip,
        "target_name": s.target_name,
        "phases": s.phases or [],
        "custom_modules": s.custom_modules or [],
        "schedule_type": s.schedule_type,
        "is_active": s.is_active,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "last_risk_score": s.last_risk_score,
    }


def _user_cond(user: Optional[User]):
    if user is not None:
        return or_(ScheduledScan.user_id == user.id, ScheduledScan.user_id.is_(None))
    return ScheduledScan.user_id.is_(None)


@router.get("/")
async def list_schedules(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """List scheduled scans for the current user (or demo/global)."""
    try:
        result = await db.execute(
            select(ScheduledScan)
            .where(_user_cond(user))
            .order_by(ScheduledScan.created_at.desc())
        )
        schedules = result.scalars().all()
        return [_serialize(s) for s in schedules]
    except Exception:
        return []


@router.post("/")
async def create_schedule(
    body: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Create a new scheduled scan."""
    next_run_at = datetime.now(timezone.utc) + _interval(body.schedule_type)

    sched = ScheduledScan(
        user_id=user.id if user else None,
        target_ip=body.target_ip,
        target_name=body.target_name,
        phases=body.phases or [],
        custom_modules=body.custom_modules or [],
        schedule_type=body.schedule_type,
        is_active=True,
        next_run_at=next_run_at,
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)
    return _serialize(sched)


@router.patch("/{schedule_id}")
async def toggle_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Toggle the is_active flag of a scheduled scan."""
    result = await db.execute(
        select(ScheduledScan).where(ScheduledScan.id == schedule_id).where(_user_cond(user))
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Planning niet gevonden")

    sched.is_active = not sched.is_active
    await db.commit()
    await db.refresh(sched)
    return _serialize(sched)


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Delete a scheduled scan."""
    result = await db.execute(
        select(ScheduledScan).where(ScheduledScan.id == schedule_id).where(_user_cond(user))
    )
    sched = result.scalar_one_or_none()
    if not sched:
        raise HTTPException(status_code=404, detail="Planning niet gevonden")

    await db.delete(sched)
    await db.commit()
    return {"ok": True}
