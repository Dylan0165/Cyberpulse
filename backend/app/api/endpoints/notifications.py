"""Notification endpoints — in-app notifications (e.g. scan complete).

Login required: each user sees their own notifications plus global (NULL)
system notices.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, or_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.notification import Notification
from app.models.user import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


def _serialize(n: Notification) -> dict:
    return {
        "id": str(n.id),
        "type": n.type,
        "title": n.title,
        "message": n.message,
        "scan_id": str(n.scan_id) if n.scan_id else None,
        "is_read": n.is_read,
        "created_at": n.created_at.isoformat() if n.created_at else None,
    }


@router.get("/")
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Return the last 20 notifications for the current user (or demo/global)."""
    try:
        if user is not None:
            cond = or_(Notification.user_id == user.id, Notification.user_id.is_(None))
        else:
            cond = Notification.user_id.is_(None)
        result = await db.execute(
            select(Notification)
            .where(cond)
            .order_by(Notification.created_at.desc())
            .limit(20)
        )
        notifications = result.scalars().all()
        return [_serialize(n) for n in notifications]
    except Exception:
        return []


@router.post("/{notif_id}/read")
async def mark_read(
    notif_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Mark a single notification as read (only if owned by user or global)."""
    if user is not None:
        cond = or_(Notification.user_id == user.id, Notification.user_id.is_(None))
    else:
        cond = Notification.user_id.is_(None)

    result = await db.execute(
        select(Notification).where(Notification.id == notif_id).where(cond)
    )
    notif = result.scalar_one_or_none()
    if not notif:
        raise HTTPException(status_code=404, detail="Melding niet gevonden")

    notif.is_read = True
    await db.commit()
    return {"ok": True}


@router.post("/read-all")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_required_user),
):
    """Mark all matching notifications as read."""
    if user is not None:
        cond = or_(Notification.user_id == user.id, Notification.user_id.is_(None))
    else:
        cond = Notification.user_id.is_(None)

    await db.execute(
        update(Notification).where(cond).values(is_read=True)
    )
    await db.commit()
    return {"ok": True}
