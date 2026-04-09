"""NDA acceptance and legal compliance endpoints."""

import hashlib
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.models.user import User
from app.models.scan import Scan
from app.models.target import Target
from app.models.legal import NDAAcceptance
from app.schemas.legal import NDAAcceptRequest, NDAAcceptResponse
from app.legal.nda_text import NDA_TEXT, NDA_VERSION, ROE_VERSION
from app.services.audit import log_action

router = APIRouter(prefix="/legal", tags=["legal"])


async def _get_user(db: AsyncSession, clerk_id: str) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/nda")
async def get_nda_text():
    """Return the current NDA text for display in the frontend modal."""
    return {
        "text": NDA_TEXT,
        "nda_version": NDA_VERSION,
        "roe_version": ROE_VERSION,
    }


@router.post("/accept-nda", response_model=NDAAcceptResponse)
async def accept_nda(
    body: NDAAcceptRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Accept NDA and Rules of Engagement for a specific scan."""
    user = await _get_user(db, current_user["clerk_id"])

    # Verify scan belongs to user and is pending NDA
    result = await db.execute(
        select(Scan).where(Scan.id == body.scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "nda_required":
        raise HTTPException(status_code=400, detail=f"Scan is not awaiting NDA acceptance (status: {scan.status})")

    # Verify target belongs to user
    result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Both checkboxes must be True (also validated in schema)
    if not body.authorization_confirmed or not body.nda_accepted:
        raise HTTPException(status_code=400, detail="Both authorization and NDA acceptance are required")

    ip = await get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    # Create immutable NDA acceptance record
    nda_hash = hashlib.sha256(NDA_TEXT.encode("utf-8")).hexdigest()

    acceptance = NDAAcceptance(
        user_id=user.id,
        target_id=target.id,
        nda_version=NDA_VERSION,
        roe_version=ROE_VERSION,
        authorization_confirmed=True,
        nda_accepted=True,
        ip_address=ip,
        user_agent=user_agent,
        nda_text_hash=nda_hash,
    )
    db.add(acceptance)
    await db.flush()

    # Update scan status
    scan.nda_acceptance_id = acceptance.id
    scan.status = "verified"

    await db.commit()
    await db.refresh(acceptance)

    # Audit log
    await log_action(
        db, "nda_accepted", ip, user_id=user.id,
        resource_type="nda_acceptance", resource_id=str(acceptance.id),
        details={
            "scan_id": str(scan.id),
            "target_id": str(target.id),
            "nda_version": NDA_VERSION,
            "roe_version": ROE_VERSION,
            "nda_hash": nda_hash,
        },
        user_agent=user_agent,
    )

    return acceptance


@router.get("/acceptances")
async def list_nda_acceptances(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """List all NDA acceptances for the current user (audit trail)."""
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(NDAAcceptance)
        .where(NDAAcceptance.user_id == user.id)
        .order_by(NDAAcceptance.accepted_at.desc())
    )
    return result.scalars().all()
