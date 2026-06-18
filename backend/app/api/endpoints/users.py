"""User account endpoints and Clerk webhook handler."""

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip, get_required_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.audit import log_action
from app.core.config import get_settings

import hashlib
import hmac
import json
import secrets

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


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
        "role": getattr(u, "role", "user"),
        "created_at": u.created_at.isoformat() if u.created_at else None,
    }


def _plan_dict(u: User) -> dict:
    from app.core.plans import UNLIMITED_SCANS
    max_scans = getattr(u, "max_scans_per_month", 3) or 3
    used = getattr(u, "scans_this_month", 0) or 0
    unlimited = max_scans >= UNLIMITED_SCANS
    return {
        "plan": u.plan,
        "plan_interval": getattr(u, "plan_interval", None),
        "plan_expires_at": u.plan_expires_at.isoformat() if getattr(u, "plan_expires_at", None) else None,
        "max_targets": getattr(u, "max_targets", 1),
        "max_scans_per_month": max_scans,
        "scans_this_month": used,
        "scans_remaining": -1 if unlimited else max(0, max_scans - used),
        "unlimited_scans": unlimited,
        "custom_modules": bool(getattr(u, "custom_modules", False)),
        "scheduled_scans": bool(getattr(u, "scheduled_scans", False)),
        "role": getattr(u, "role", "user"),
        "features": {
            "custom_modules": bool(getattr(u, "custom_modules", False)),
            "scheduled_scans": bool(getattr(u, "scheduled_scans", False)),
            "white_label": bool(getattr(u, "white_label", False)),
            "ai_upgrade": getattr(u, "ai_upgrade", "deepseek"),
        },
    }


class UpdateMeBody(BaseModel):
    name: str | None = None
    company_name: str | None = None
    notify_on_complete: bool | None = None
    notification_email: str | None = None
    ai_provider: str | None = None          # deepseek | anthropic | runpod
    ai_provider_active: bool | None = None  # paid upgrade active
    ai_api_key: str | None = None           # legacy local key
    ai_base_url: str | None = None          # legacy local base url


@router.patch("/me")
async def update_me(
    body: UpdateMeBody,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    data = body.model_dump(exclude_unset=True)
    if "name" in data:
        user.name = data["name"]
    if "company_name" in data:
        user.company_name = data["company_name"]
    if "notify_on_complete" in data:
        user.notify_on_complete = data["notify_on_complete"]
    if "notification_email" in data:
        user.notification_email = data["notification_email"]
    if "ai_provider" in data and data["ai_provider"] in ("deepseek", "anthropic", "runpod", "local"):
        user.ai_provider = data["ai_provider"]
    if "ai_provider_active" in data and data["ai_provider_active"] is not None:
        user.ai_provider_active = bool(data["ai_provider_active"])
    if "ai_api_key" in data:
        user.ai_api_key = data["ai_api_key"] or None
    if "ai_base_url" in data:
        user.ai_base_url = data["ai_base_url"] or None
    await db.commit()
    await db.refresh(user)
    return _user_dict(user)


@router.post("/me/regenerate-api-key")
async def regenerate_api_key(
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    user.api_key = secrets.token_hex(32)
    await db.commit()
    return {"api_key": user.api_key}


@router.get("/me/plan")
async def get_my_plan(user: User = Depends(get_required_user)):
    """Current plan + usage for the dashboard plan widget and gating."""
    return _plan_dict(user)


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    result = await db.execute(
        select(User).where(User.clerk_id == current_user["clerk_id"])
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found. Please complete registration.")
    return user


@router.post("/webhooks/clerk")
async def clerk_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    """Handle Clerk webhook events for user sync."""
    payload = await request.body()

    # Verify webhook signature
    svix_id = request.headers.get("svix-id", "")
    svix_timestamp = request.headers.get("svix-timestamp", "")
    svix_signature = request.headers.get("svix-signature", "")

    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(status_code=400, detail="Missing webhook headers")

    # Parse payload
    try:
        data = json.loads(payload)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event_type = data.get("type", "")
    event_data = data.get("data", {})

    if event_type == "user.created":
        clerk_id = event_data.get("id", "")
        email = ""
        email_addresses = event_data.get("email_addresses", [])
        for ea in email_addresses:
            if ea.get("id") == event_data.get("primary_email_address_id"):
                email = ea.get("email_address", "")
                break

        full_name = f"{event_data.get('first_name', '')} {event_data.get('last_name', '')}".strip()

        # Create user
        user = User(
            clerk_id=clerk_id,
            email=email,
            full_name=full_name or None,
            plan="free",
            credits=1,  # 1 free scan credit for new users
        )
        db.add(user)
        await db.commit()

    elif event_type == "user.updated":
        clerk_id = event_data.get("id", "")
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            email_addresses = event_data.get("email_addresses", [])
            for ea in email_addresses:
                if ea.get("id") == event_data.get("primary_email_address_id"):
                    user.email = ea.get("email_address", user.email)
                    break
            full_name = f"{event_data.get('first_name', '')} {event_data.get('last_name', '')}".strip()
            if full_name:
                user.full_name = full_name
            await db.commit()

    elif event_type == "user.deleted":
        clerk_id = event_data.get("id", "")
        result = await db.execute(select(User).where(User.clerk_id == clerk_id))
        user = result.scalar_one_or_none()
        if user:
            user.is_active = False
            await db.commit()

    return {"status": "ok"}
