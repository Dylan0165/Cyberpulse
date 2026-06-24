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

# ── Credit packages (single source of truth) ────────────────────────────────
# One-time purchases, price in eurocents. Credits never expire. `popular` marks
# the recommended pack. The losse_scan price (€100) is the per-scan reference
# used to compute the savings shown on the larger packs.
CREDIT_PACKAGES: dict[str, dict] = {
    "losse_scan": {"credits": 1,  "price": 10000,  "label": "Losse Scan", "popular": False},
    "starter":    {"credits": 3,  "price": 25000,  "label": "Starter",    "popular": False},
    "groei":      {"credits": 5,  "price": 37500,  "label": "Groei",      "popular": True},
    "pro":        {"credits": 10, "price": 65000,  "label": "Pro",        "popular": False},
    "expert":     {"credits": 25, "price": 125000, "label": "Expert",     "popular": False},
}

# Per-scan reference price (eurocents) = the single-scan package price.
_REFERENCE_PRICE = CREDIT_PACKAGES["losse_scan"]["price"]


def package_view(key: str, pkg: dict) -> dict:
    """A package enriched with derived per-scan price and savings (eurocents)."""
    per_scan = pkg["price"] // pkg["credits"]
    savings = _REFERENCE_PRICE * pkg["credits"] - pkg["price"]
    return {
        "key": key,
        "label": pkg["label"],
        "credits": pkg["credits"],
        "price": pkg["price"],
        "popular": pkg["popular"],
        "price_per_scan": per_scan,
        "savings": max(0, savings),
    }


def packages_payload() -> list[dict]:
    """All packages as an ordered list for the API / frontend."""
    return [package_view(k, p) for k, p in CREDIT_PACKAGES.items()]


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
    async def get_balance(db: AsyncSession, user_id: uuid.UUID) -> dict:
        """Balance snapshot: {credits_remaining, credits_total, plan, is_unlimited}."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return {"credits_remaining": 0, "credits_total": 0, "plan": "trial", "is_unlimited": False}
        unlimited = _is_unlimited(user)
        return {
            "credits_remaining": UNLIMITED_SENTINEL if unlimited else int(getattr(user, "credits_remaining", 0) or 0),
            "credits_total": int(getattr(user, "credits_total", 0) or 0),
            "plan": getattr(user, "plan", "trial") or "trial",
            "is_unlimited": unlimited,
        }

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
