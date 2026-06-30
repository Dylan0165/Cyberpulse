"""Seed / reset a ready-to-use test account.

Idempotent: creates the test account or resets it to a known state — admin role,
enterprise plan, unlimited credits, 2FA off, terms + onboarding done, plus a
pre-verified scanme.nmap.org target. Shared by the admin endpoint and the
scripts/create_test_account.py CLI so there is a single source of truth.
"""

from __future__ import annotations

import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import hash_password
from app.core.plans import apply_plan_limits
from app.models.user import User
from app.models.target import Target

TEST_EMAIL = "test@scanix.nl"
TEST_PASSWORD = "ScanixTest2026!"
TEST_TARGET = "scanme.nmap.org"
UNLIMITED = 999999


async def create_or_reset_test_account(db: AsyncSession) -> dict:
    now = datetime.now(timezone.utc)

    result = await db.execute(select(User).where(User.email == TEST_EMAIL))
    user = result.scalar_one_or_none()
    created = user is None

    if user is None:
        user = User(
            email=TEST_EMAIL,
            clerk_id=f"local-test-{uuid.uuid4()}",
            api_key=secrets.token_hex(32),
        )
        db.add(user)

    # Always reset to the known test state.
    user.name = "Scanix Test"
    user.full_name = "Scanix Test"
    user.company_name = "Scanix"
    user.password_hash = hash_password(TEST_PASSWORD)
    user.is_active = True
    user.role = "admin"
    user.terms_accepted = True
    user.terms_accepted_at = now
    user.onboarding_completed = True
    # Enterprise = unlimited scans + all modules + 20 targets + white-label.
    apply_plan_limits(user, "enterprise")
    user.plan_started_at = now
    user.plan_expires_at = None
    user.credits_remaining = UNLIMITED
    user.credits_total = UNLIMITED
    # 2FA off so test logins are fast.
    user.totp_enabled = False
    user.totp_secret = None
    user.totp_backup_codes = None

    await db.flush()

    # Pre-verified test target (skip ownership verification during testing).
    tgt_res = await db.execute(
        select(Target).where(Target.user_id == user.id, Target.value == TEST_TARGET)
    )
    target = tgt_res.scalar_one_or_none()
    if target is None:
        target = Target(
            user_id=user.id,
            name="Scanix Test Target",
            target_type="domain",
            value=TEST_TARGET,
            is_verified=True,
        )
        db.add(target)
    else:
        target.is_verified = True
    # Best-effort verification metadata if the columns exist.
    for attr, val in (("verified_at", now), ("verification_method", "seed")):
        if hasattr(target, attr):
            setattr(target, attr, val)

    await db.commit()
    await db.refresh(user)

    return {
        "created": created,
        "reset": not created,
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "plan": user.plan,
        "role": user.role,
        "credits_remaining": user.credits_remaining,
        "credits_total": user.credits_total,
        "target": TEST_TARGET,
        "target_verified": True,
        "admin": True,
        "twofa_enabled": False,
    }


def banner(info: dict) -> str:
    return (
        "\n=== TEST ACCOUNT KLAAR ===\n"
        f"URL:        http://localhost:3000\n"
        f"Email:      {info['email']}\n"
        f"Wachtwoord: {info['password']}\n"
        f"Credits:    {info['credits_remaining']}\n"
        f"Target:     {info['target']} (geverifieerd)\n"
        f"Admin:      Ja\n"
        f"Plan:       {info['plan']}\n"
        f"({'aangemaakt' if info['created'] else 'gereset'})\n"
    )
