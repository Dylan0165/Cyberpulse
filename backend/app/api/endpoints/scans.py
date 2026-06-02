"""Scan management endpoints — create, list, control scans."""

import json
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.core.redis import get_redis
from app.models.scan import Scan
from app.models.target import Target
from app.models.user import User
from app.models.legal import NDAAcceptance
from app.schemas.scan import (
    ScanCreate,
    ScanResponse,
    ScanListResponse,
    ScanReportResponse,
    QUICK_PHASES,
    FULL_PHASES,
)
from app.services.audit import log_action

router = APIRouter(prefix="/scans", tags=["scans"])


async def _get_user(db: AsyncSession, clerk_id: str) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=ScanResponse)
async def create_scan(
    body: ScanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    # Get target and verify ownership
    result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # ENFORCEMENT: Target must be verified
    if not target.is_verified:
        raise HTTPException(status_code=403, detail="Target must be verified before scanning")

    # Determine phases
    if body.scan_type == "quick":
        phases = QUICK_PHASES
    elif body.scan_type == "full":
        phases = FULL_PHASES
    else:
        phases = body.phases or QUICK_PHASES

    # Merge scan_mode, target_type, credentials into config
    config = dict(body.config)
    config["scan_mode"]   = body.scan_mode
    config["target_type"] = body.target_type
    # Credentials stored in config — never logged or exposed in responses
    if body.credentials:
        config["credentials"] = body.credentials

    scan = Scan(
        user_id=user.id,
        target_id=body.target_id,
        scan_type=body.scan_type,
        phases=phases,
        config=config,
        save_report=body.save_report,
        status="nda_required",
    )
    db.add(scan)

    await db.commit()
    await db.refresh(scan)

    ip = await get_client_ip(request)
    await log_action(
        db, "scan_created", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan.id),
        details={"scan_type": body.scan_type, "target": target.value},
    )

    return scan


@router.get("/", response_model=ScanListResponse)
async def list_scans(
    page: int = 1,
    page_size: int = 20,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    total = await db.scalar(
        select(func.count(Scan.id)).where(Scan.user_id == user.id)
    )
    result = await db.execute(
        select(Scan)
        .where(Scan.user_id == user.id)
        .order_by(Scan.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    scans = result.scalars().all()

    return ScanListResponse(scans=scans, total=total, page=page, page_size=page_size)


@router.get("/{scan_id}", response_model=ScanResponse)
async def get_scan(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan


@router.post("/{scan_id}/start")
async def start_scan(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Start a scan after NDA acceptance. The scan must have an associated NDA acceptance."""
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status != "verified":
        raise HTTPException(status_code=400, detail=f"Scan cannot be started in status '{scan.status}'. NDA must be accepted first.")

    # Verify NDA acceptance exists
    if not scan.nda_acceptance_id:
        raise HTTPException(status_code=400, detail="NDA must be accepted before starting scan")

    scan.status = "pending"
    await db.commit()

    # Queue the scan task
    from app.workers.scan_tasks import run_scan
    run_scan.delay(str(scan.id))

    ip = await get_client_ip(request)
    await log_action(
        db, "scan_started", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan.id),
    )

    return {"message": "Scan queued", "scan_id": str(scan.id)}


@router.post("/{scan_id}/cancel")
async def cancel_scan(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status not in ("running", "analyzing", "pending"):
        raise HTTPException(status_code=400, detail="Scan is not running")

    # Stop container if running
    if scan.container_id:
        from app.services.scanner import stop_scan_container
        stop_scan_container(scan.container_id)

    scan.status = "cancelled"
    scan.completed_at = datetime.now(timezone.utc)
    await db.commit()

    ip = await get_client_ip(request)
    await log_action(
        db, "scan_cancelled", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan.id),
    )

    return {"message": "Scan cancelled"}


@router.get("/{scan_id}/report", response_model=ScanReportResponse)
async def get_report(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    ip = await get_client_ip(request)
    await log_action(
        db, "report_viewed", ip, user_id=user.id,
        resource_type="scan", resource_id=str(scan.id),
    )

    # Check if report is in DB (saved)
    if scan.report_data:
        return ScanReportResponse(
            scan_id=scan.id,
            report_data=scan.report_data,
            security_score=scan.security_score,
            generated_at=scan.completed_at,
        )

    # Check Redis temporary store
    redis = await get_redis()
    cached = await redis.get(f"scan:{scan_id}:report")
    if cached:
        return ScanReportResponse(
            scan_id=scan.id,
            report_data=json.loads(cached),
            security_score=scan.security_score,
            generated_at=scan.completed_at,
        )

    raise HTTPException(status_code=404, detail="Report not available. It may have expired.")


@router.post("/{scan_id}/share")
async def create_share_link(
    scan_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Scan).where(Scan.id == scan_id, Scan.user_id == user.id)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if not scan.save_report or not scan.report_data:
        raise HTTPException(status_code=400, detail="Report must be saved to create a share link")

    scan.share_token = secrets.token_urlsafe(32)
    scan.share_expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    await db.commit()

    from app.core.config import get_settings
    settings = get_settings()
    share_url = f"{settings.frontend_url}/reports/shared/{scan.share_token}"

    return {"share_url": share_url, "expires_at": scan.share_expires_at.isoformat()}


@router.get("/shared/{share_token}")
async def get_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    """Public endpoint — no auth required. Returns shared report if token is valid."""
    result = await db.execute(
        select(Scan).where(Scan.share_token == share_token)
    )
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Report not found")

    if scan.share_expires_at and scan.share_expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=410, detail="Share link has expired")

    if not scan.report_data:
        raise HTTPException(status_code=404, detail="Report data not available")

    return {
        "report_data": scan.report_data,
        "security_score": scan.security_score,
        "scan_type": scan.scan_type,
        "completed_at": scan.completed_at.isoformat() if scan.completed_at else None,
    }
