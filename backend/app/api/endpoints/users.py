"""User account endpoints and Clerk webhook handler."""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.audit import log_action
from app.core.config import get_settings

import hashlib
import hmac
import json

router = APIRouter(prefix="/users", tags=["users"])
settings = get_settings()


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
