"""Team members — invite colleagues to an account (migration 0013).

Roles: viewer / analyst / admin. Invites are by email; an invitee accepts once
logged in with the matching email. NOTE: cross-account resource sharing (a
member acting on the owner's scans) is modelled here but not yet enforced
across every endpoint — that wiring is a follow-up.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.user import User
from app.models.team import TeamMember, VALID_ROLES

router = APIRouter(prefix="/teams", tags=["teams"])

_ALLOWED_PLANS = ("business", "enterprise", "admin")


class InviteBody(BaseModel):
    email: str
    role: str = "viewer"


def _dict(m: TeamMember) -> dict:
    return {
        "id": str(m.id),
        "email": m.email,
        "role": m.role,
        "member_id": str(m.member_id) if m.member_id else None,
        "status": "accepted" if m.accepted_at else "pending",
        "invited_at": m.invited_at.isoformat() if m.invited_at else None,
        "accepted_at": m.accepted_at.isoformat() if m.accepted_at else None,
    }


@router.post("/invite")
async def invite_member(body: InviteBody, user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    if getattr(user, "plan", None) not in _ALLOWED_PLANS:
        raise HTTPException(status_code=403, detail={
            "error": "plan_required",
            "message": "Teamleden zijn beschikbaar vanaf het Business-pakket.",
            "upgrade_url": "/billing",
        })
    role = body.role if body.role in VALID_ROLES else "viewer"
    email = body.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Ongeldig e-mailadres")

    existing = await db.execute(
        select(TeamMember).where(TeamMember.owner_id == user.id, TeamMember.email == email)
    )
    member = existing.scalar_one_or_none()
    if member:
        member.role = role  # re-invite updates role
    else:
        member = TeamMember(owner_id=user.id, email=email, role=role)
        db.add(member)
    await db.commit()
    await db.refresh(member)

    # Best-effort invite email (no-ops without SMTP).
    try:
        from app.services.email_service import email_service, APP_URL
        html = (
            f"<p>U bent uitgenodigd voor een Scanix-team als <strong>{role}</strong>.</p>"
            f'<p><a href="{APP_URL}/settings">Open Scanix</a> en log in met dit e-mailadres om de uitnodiging te accepteren.</p>'
        )
        import asyncio as _aio
        _aio.create_task(email_service.send(email, "Uitnodiging voor een Scanix-team", html))
    except Exception:
        pass

    return _dict(member)


@router.post("/accept/{member_id}")
async def accept_invite(member_id: uuid.UUID, user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TeamMember).where(TeamMember.id == member_id))
    member = res.scalar_one_or_none()
    if not member or member.email.lower() != (user.email or "").lower():
        raise HTTPException(status_code=404, detail="Uitnodiging niet gevonden")
    member.member_id = user.id
    member.accepted_at = datetime.now(timezone.utc)
    await db.commit()
    return _dict(member)


@router.get("/members")
async def list_members(user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(TeamMember).where(TeamMember.owner_id == user.id).order_by(TeamMember.invited_at.desc())
    )
    return [_dict(m) for m in res.scalars().all()]


@router.get("/my-memberships")
async def my_memberships(user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    """Teams this user belongs to (accepted invites)."""
    res = await db.execute(
        select(TeamMember).where(
            or_(TeamMember.member_id == user.id, TeamMember.email == (user.email or "").lower())
        )
    )
    return [_dict(m) for m in res.scalars().all()]


@router.delete("/members/{member_id}")
async def remove_member(member_id: uuid.UUID, user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(TeamMember).where(TeamMember.id == member_id, TeamMember.owner_id == user.id))
    member = res.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=404, detail="Teamlid niet gevonden")
    await db.delete(member)
    await db.commit()
    return {"removed": True}
