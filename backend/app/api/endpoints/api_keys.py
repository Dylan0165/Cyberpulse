"""Customer API keys. Only the SHA-256 hash is stored; the plaintext key is
shown exactly once at creation."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.models.user import User
from app.models.api_key import ApiKey, VALID_SCOPES

router = APIRouter(prefix="/api-keys", tags=["api-keys"])


def hash_key(plaintext: str) -> str:
    return hashlib.sha256(plaintext.encode()).hexdigest()


class CreateKeyBody(BaseModel):
    name: str
    scopes: list[str] | None = None
    expires_in_days: int | None = None


def _dict(k: ApiKey) -> dict:
    return {
        "id": str(k.id),
        "name": k.name,
        "prefix": k.key_prefix,
        "scopes": k.scopes or [],
        "last_used": k.last_used.isoformat() if k.last_used else None,
        "expires_at": k.expires_at.isoformat() if k.expires_at else None,
        "is_active": k.is_active,
        "created_at": k.created_at.isoformat() if k.created_at else None,
    }


@router.post("")
@router.post("/")
async def create_key(body: CreateKeyBody, user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    scopes = [s for s in (body.scopes or ["scan:read", "scan:create"]) if s in VALID_SCOPES]
    if not scopes:
        raise HTTPException(status_code=400, detail="Geen geldige scopes opgegeven")
    plaintext = "sx_live_" + secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        if body.expires_in_days else None
    )
    key = ApiKey(
        user_id=user.id,
        name=body.name.strip() or "API key",
        key_hash=hash_key(plaintext),
        key_prefix=plaintext[:12],
        scopes=scopes,
        expires_at=expires_at,
    )
    db.add(key)
    await db.commit()
    await db.refresh(key)
    # Plaintext returned ONCE.
    return {"id": str(key.id), "key": plaintext, "name": key.name, "prefix": key.key_prefix, "scopes": scopes}


@router.get("")
@router.get("/")
async def list_keys(user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(ApiKey).where(ApiKey.user_id == user.id, ApiKey.is_active == True).order_by(ApiKey.created_at.desc())  # noqa: E712
    )
    return [_dict(k) for k in res.scalars().all()]


@router.delete("/{key_id}")
async def revoke_key(key_id: uuid.UUID, user: User = Depends(get_required_user), db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(ApiKey).where(ApiKey.id == key_id, ApiKey.user_id == user.id))
    key = res.scalar_one_or_none()
    if not key:
        raise HTTPException(status_code=404, detail="API key niet gevonden")
    key.is_active = False
    await db.commit()
    return {"revoked": True}
