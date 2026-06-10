"""Scan management endpoints — school project, no auth/NDA/verification required."""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.core.redis import get_redis
from app.models.scan import Scan
from app.models.target import Target
from app.models.user import User
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

_STUDENT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


async def _student_user(db: AsyncSession) -> User:
    result = await db.execute(select(User).where(User.id == _STUDENT_USER_ID))
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        id=_STUDENT_USER_ID,
        clerk_id="student",
        email="student@cyberpulse.local",
        full_name="Student",
        plan="professional",
        credits=9999,
        max_concurrent_scans=10,
        is_active=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.post("/", response_model=ScanResponse)
async def create_scan(
    body: ScanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _student_user(db)

    # Verify target exists (no ownership check)
    result = await db.execute(select(Target).where(Target.id == body.target_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    # Determine Kali phases from preset, then append any custom modules
    # from body.phases so user-selected m09-m14 are never dropped.
    _CUSTOM_MODULE_IDS = {"m09", "m10", "m11", "m12", "m13", "m14"}
    if body.scan_type == "quick":
        phases = list(QUICK_PHASES)
    elif body.scan_type == "full":
        phases = list(FULL_PHASES)
    else:
        phases = list(body.phases or QUICK_PHASES)
    # Always preserve custom module selections regardless of preset
    for p in (body.phases or []):
        if p in _CUSTOM_MODULE_IDS and p not in phases:
            phases.append(p)

    config = dict(body.config) if body.config else {}
    config["scan_mode"]   = body.scan_mode
    config["target_type"] = body.target_type
    if body.credentials:
        config["credentials"] = body.credentials

    scan = Scan(
        user_id=user.id,
        target_id=body.target_id,
        scan_type=body.scan_type,
        phases=phases,
        config=config,
        save_report=True,  # always save — school project, no billing per report
        status="pending",       # skip NDA/verification flow
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
    total = await db.scalar(select(func.count(Scan.id)))
    result = await db.execute(
        select(Scan)
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
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
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
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status not in ("pending", "nda_required", "verified"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot start scan in status '{scan.status}'"
        )

    scan.status = "pending"
    await db.commit()

    from app.workers.scan_tasks import run_scan
    run_scan.delay(str(scan.id))

    ip = await get_client_ip(request)
    await log_action(
        db, "scan_started", ip, user_id=_STUDENT_USER_ID,
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
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.status not in ("running", "analyzing", "pending"):
        raise HTTPException(status_code=400, detail="Scan is not running")

    if scan.container_id:
        try:
            from app.services.scanner import stop_scan_container
            stop_scan_container(scan.container_id)
        except Exception:
            pass

    scan.status = "cancelled"
    scan.completed_at = datetime.now(timezone.utc)
    await db.commit()

    return {"message": "Scan cancelled"}


@router.get("/{scan_id}/report", response_model=ScanReportResponse)
async def get_report(
    scan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(select(Scan).where(Scan.id == scan_id))
    scan = result.scalar_one_or_none()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")

    if scan.report_data:
        return ScanReportResponse(
            scan_id=scan.id,
            report_data=scan.report_data,
            security_score=scan.security_score,
            generated_at=scan.completed_at,
        )

    redis = await get_redis()
    cached = await redis.get(f"scan:{scan_id}:report")
    if cached:
        return ScanReportResponse(
            scan_id=scan.id,
            report_data=json.loads(cached),
            security_score=scan.security_score,
            generated_at=scan.completed_at,
        )

    raise HTTPException(status_code=404, detail="Report not available yet.")


@router.get("/shared/{share_token}")
async def get_shared_report(
    share_token: str,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Scan).where(Scan.share_token == share_token))
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
