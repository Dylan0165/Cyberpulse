"""Target management endpoints — CRUD + ownership verification."""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.models.target import Target
from app.models.user import User
from app.schemas.target import (
    TargetCreate,
    TargetResponse,
    VerifyDNSRequest,
    VerifyFileRequest,
    VerifyIPDeclarationRequest,
)
from app.legal.verification import (
    generate_verification_token,
    verify_dns_txt,
    verify_file_upload,
    verify_ip_declaration,
    validate_target_value,
)
from app.services.audit import log_action

router = APIRouter(prefix="/targets", tags=["targets"])


async def _get_user(db: AsyncSession, clerk_id: str) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.post("/", response_model=TargetResponse)
async def create_target(
    body: TargetCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    # Validate target value
    if not validate_target_value(body.target_type, body.value):
        raise HTTPException(status_code=400, detail="Invalid target value for the specified type")

    # Generate verification token
    token = await generate_verification_token()

    target = Target(
        user_id=user.id,
        name=body.name,
        target_type=body.target_type,
        value=body.value,
        scope=body.scope.model_dump() if body.scope else {},
        verification_token=token,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)

    ip = await get_client_ip(request)
    await log_action(
        db, "target_created", ip, user_id=user.id,
        resource_type="target", resource_id=str(target.id),
    )

    return target


@router.get("/", response_model=list[TargetResponse])
async def list_targets(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.user_id == user.id).order_by(Target.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{target_id}", response_model=TargetResponse)
async def get_target(
    target_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return target


@router.delete("/{target_id}")
async def delete_target(
    target_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.id == target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    await db.delete(target)
    await db.commit()

    ip = await get_client_ip(request)
    await log_action(
        db, "target_deleted", ip, user_id=user.id,
        resource_type="target", resource_id=str(target_id),
    )

    return {"message": "Target deleted"}


@router.post("/verify/dns", response_model=TargetResponse)
async def verify_target_dns(
    body: VerifyDNSRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    success = await verify_dns_txt(target, db)
    if not success:
        raise HTTPException(status_code=400, detail="DNS TXT verification failed. Ensure the record exists.")

    ip = await get_client_ip(request)
    await log_action(
        db, "target_verified", ip, user_id=user.id,
        resource_type="target", resource_id=str(target.id),
        details={"method": "dns_txt"},
    )

    await db.refresh(target)
    return target


@router.post("/verify/file", response_model=TargetResponse)
async def verify_target_file(
    body: VerifyFileRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    success = await verify_file_upload(target, db)
    if not success:
        raise HTTPException(status_code=400, detail="File verification failed. Ensure the file exists at /.well-known/autopentest.txt")

    ip = await get_client_ip(request)
    await log_action(
        db, "target_verified", ip, user_id=user.id,
        resource_type="target", resource_id=str(target.id),
        details={"method": "file_upload"},
    )

    await db.refresh(target)
    return target


@router.post("/verify/ip-declaration", response_model=TargetResponse)
async def verify_target_ip_declaration(
    body: VerifyIPDeclarationRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])
    result = await db.execute(
        select(Target).where(Target.id == body.target_id, Target.user_id == user.id)
    )
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")

    success = await verify_ip_declaration(target, db)
    if not success:
        raise HTTPException(status_code=400, detail="IP declaration verification failed")

    ip = await get_client_ip(request)
    await log_action(
        db, "target_verified", ip, user_id=user.id,
        resource_type="target", resource_id=str(target.id),
        details={"method": "legal_declaration"},
    )

    await db.refresh(target)
    return target
