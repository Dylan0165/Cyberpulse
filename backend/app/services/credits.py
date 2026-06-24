"""Prepaid credits service.

1 credit = 1 scan. Credits never expire. Business/Enterprise plans are
unlimited (a sentinel balance of 999999, never decremented).

Concurrency: deduct_credit locks the user row with SELECT ... FOR UPDATE so two
scans started at the same moment cannot both succeed on a single remaining
credit. The decrement and the credit_usage ledger row are written in the
caller's transaction and committed together with the scan.
"""

from __future__ import annotations

import os
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.credits import ScanCredit, CreditUsage

UNLIMITED_PLANS = {"business", "enterprise"}
UNLIMITED_SENTINEL = 999999

_NO_CREDITS_DETAIL = {
    "error": "no_credits",
    "message": "U heeft geen scan credits meer. Koop credits om door te gaan.",
    "buy_url": "/billing",
}


def use_credits_model() -> bool:
    """Feature flag — when false, the legacy subscription flow stays active."""
    return os.getenv("USE_CREDITS_MODEL", "true").strip().lower() in {"1", "true", "yes", "on"}


def _is_unlimited(user: User) -> bool:
    return getattr(user, "plan", None) in UNLIMITED_PLANS


class CreditsService:
    @staticmethod
    async def get_balance(db: AsyncSession, user_id: uuid.UUID) -> int:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return 0
        if _is_unlimited(user):
            return UNLIMITED_SENTINEL
        return int(getattr(user, "credits_remaining", 0) or 0)

    @staticmethod
    async def has_credits(db: AsyncSession, user_id: uuid.UUID) -> bool:
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False
        if _is_unlimited(user):
            return True
        return int(getattr(user, "credits_remaining", 0) or 0) > 0

    @staticmethod
    async def deduct_credit(
        db: AsyncSession,
        user_id: uuid.UUID,
        scan_id: uuid.UUID,
        amount: int = 1,
    ) -> bool:
        """Atomically spend `amount` credits for a scan.

        Raises HTTPException(402) when the user has no credits. Does NOT commit —
        the caller commits together with the scan row. The user row is locked
        FOR UPDATE for the duration of the surrounding transaction.
        """
        # Lock the user row so concurrent scans serialise on the balance.
        result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=402, detail=_NO_CREDITS_DETAIL)

        unlimited = _is_unlimited(user)
        if not unlimited:
            remaining = int(getattr(user, "credits_remaining", 0) or 0)
            if remaining < amount:
                raise HTTPException(status_code=402, detail=_NO_CREDITS_DETAIL)
            user.credits_remaining = remaining - amount

        # Ledger row (also recorded for unlimited plans, for usage analytics).
        db.add(
            CreditUsage(
                user_id=user_id,
                scan_id=scan_id,
                credits_used=amount,
            )
        )
        await db.flush()
        return True

    @staticmethod
    async def add_credits(
        db: AsyncSession,
        user_id: uuid.UUID,
        amount: int,
        package_name: str,
        price_paid: int,
        stripe_payment_id: str,
    ) -> ScanCredit | None:
        """Grant credits and record the purchase. Idempotent on stripe_payment_id.

        Returns the created ScanCredit, or None when this payment was already
        processed (duplicate webhook delivery). Commits on success.
        """
        # Idempotency: never add the same payment twice.
        dupe = await db.execute(
            select(ScanCredit).where(ScanCredit.stripe_payment_id == stripe_payment_id)
        )
        if dupe.scalar_one_or_none() is not None:
            return None

        result = await db.execute(
            select(User).where(User.id == user_id).with_for_update()
        )
        user = result.scalar_one_or_none()
        if not user:
            raise HTTPException(status_code=404, detail="Gebruiker niet gevonden")

        user.credits_remaining = int(getattr(user, "credits_remaining", 0) or 0) + amount
        user.credits_total = int(getattr(user, "credits_total", 0) or 0) + amount
        # A trial user who buys credits becomes a regular credits user.
        if getattr(user, "plan", None) == "trial":
            user.plan = "credits"

        record = ScanCredit(
            user_id=user_id,
            package_name=package_name,
            credits_purchased=amount,
            price_paid=price_paid,
            stripe_payment_id=stripe_payment_id,
        )
        db.add(record)
        await db.commit()
        await db.refresh(record)
        return record


credits_service = CreditsService()
