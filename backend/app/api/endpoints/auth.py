"""Real (permissive) authentication endpoints.

Register / login / logout with httpOnly JWT cookie (cp_token), plus
profile, terms acceptance and onboarding completion. Dutch error messages,
English code/logs. Async SQLAlchemy throughout.
"""

import logging
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.ratelimit import limiter

logger = logging.getLogger(__name__)

from app.core.database import get_db
from app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_required_user,
    JWT_EXPIRY_DAYS,
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["auth"])

_COOKIE_MAX_AGE = JWT_EXPIRY_DAYS * 24 * 3600


# ── Pydantic bodies ──────────────────────────────────────────────────────────

class RegisterBody(BaseModel):
    email: str
    password: str
    name: str
    company_name: str | None = None


class LoginBody(BaseModel):
    email: str
    password: str


class AcceptTermsBody(BaseModel):
    version: str = "1.0"


# ── Helpers ──────────────────────────────────────────────────────────────────

def _user_dict(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "name": u.name or u.full_name,
        "company_name": u.company_name or u.company,
        "api_key": u.api_key,
        "terms_accepted": u.terms_accepted,
        "terms_accepted_at": u.terms_accepted_at.isoformat() if u.terms_accepted_at else None,
        "onboarding_completed": u.onboarding_completed,
        "notify_on_complete": u.notify_on_complete,
        "notification_email": u.notification_email,
        "ai_provider": getattr(u, "ai_provider", "deepseek") or "deepseek",
        "ai_provider_active": bool(getattr(u, "ai_provider_active", False)),
        "ai_base_url": getattr(u, "ai_base_url", None),
        "ai_api_key_set": bool(getattr(u, "ai_api_key", None)),
        "plan": u.plan,
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _set_token_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key="cp_token",
        value=token,
        httponly=True,
        max_age=_COOKIE_MAX_AGE,
        samesite="lax",
    )


# ── Endpoints ────────────────────────────────────────────────────────────────

@router.post("/register")
@limiter.limit("5/minute")
async def register(
    request: Request,
    body: RegisterBody,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    try:
        existing = await db.execute(select(User).where(User.email == body.email))
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(status_code=400, detail="E-mailadres is al in gebruik")

        user = User(
            email=body.email,
            name=body.name,
            full_name=body.name,
            company_name=body.company_name,
            company=body.company_name,
            password_hash=hash_password(body.password),
            api_key=secrets.token_hex(32),
            clerk_id=f"local-{uuid.uuid4()}",
            is_active=True,
            plan="professional",
            credits=9999,
            terms_accepted=False,
            onboarding_completed=False,
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    except HTTPException:
        raise
    except Exception as exc:
        await db.rollback()
        logger.exception("Registration failed for %s", body.email)
        # Surface a hint if the DB schema is behind (migration 0003 not applied)
        msg = str(exc).lower()
        if "column" in msg or "does not exist" in msg or "undefined" in msg:
            raise HTTPException(
                status_code=500,
                detail="Database is nog niet bijgewerkt. Voer de migratie uit (alembic upgrade head) en probeer opnieuw.",
            )
        raise HTTPException(status_code=500, detail="Registratie mislukt. Probeer het later opnieuw.")

    token = create_access_token(user.id, user.email)
    _set_token_cookie(response, token)
    return {"user": _user_dict(user), "token": token}


@router.post("/login")
@limiter.limit("10/minute")
async def login(
    request: Request,
    body: LoginBody,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()
    if user is None or not user.password_hash or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Ongeldig e-mailadres of wachtwoord")

    token = create_access_token(user.id, user.email)
    _set_token_cookie(response, token)
    return {"user": _user_dict(user), "token": token}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("cp_token")
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_required_user)):
    return _user_dict(user)


@router.post("/accept-terms")
async def accept_terms(
    body: AcceptTermsBody,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    user.terms_accepted = True
    user.terms_accepted_at = datetime.now(timezone.utc)
    user.terms_version = body.version
    await db.commit()
    return {"ok": True}


@router.post("/complete-onboarding")
async def complete_onboarding(
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    user.onboarding_completed = True
    await db.commit()
    return {"ok": True}
