"""Stripe billing endpoints for Scanix.

Robustness contract: every Stripe interaction is guarded so that a missing or
misconfigured Stripe setup returns a clean 503 with a Dutch message instead of
leaking a 500 stack trace to the user. The webhook never fails on best-effort
side tasks (e.g. e-mail) — it only returns 400 on a bad signature.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_required_user
from app.core.plans import apply_plan_limits
from app.models.user import User
from app.models.credits import ScanCredit
from app.services.credits import credits_service, CREDIT_PACKAGES, packages_payload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])

# App URL for Stripe redirects (kept consistent with the billing portal).
_APP_URL = os.getenv("APP_PUBLIC_URL", "https://app.scanix.nl")

# Generic Dutch message shown whenever payments are unavailable / misconfigured.
_NOT_CONFIGURED = (
    "Betalingen zijn nog niet geconfigureerd. "
    "Neem contact op via info@scanix.nl"
)

# Number of days each billing interval grants.
_INTERVAL_DAYS = {"monthly": 30, "quarterly": 90, "yearly": 365}

# Credit packages live in app.services.credits (single source of truth).


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _price_map() -> dict[str, str]:
    """Return a map of '{plan}_{interval}' -> Stripe price id from env."""
    return {
        "starter_monthly": os.getenv("STRIPE_STARTER_MONTHLY", ""),
        "starter_quarterly": os.getenv("STRIPE_STARTER_QUARTERLY", ""),
        "starter_yearly": os.getenv("STRIPE_STARTER_YEARLY", ""),
        "business_monthly": os.getenv("STRIPE_BUSINESS_MONTHLY", ""),
        "business_quarterly": os.getenv("STRIPE_BUSINESS_QUARTERLY", ""),
        "business_yearly": os.getenv("STRIPE_BUSINESS_YEARLY", ""),
    }


def _plan_interval_from_price_id(price_id: str | None) -> tuple[str | None, str | None]:
    """Reverse-lookup a Stripe price id back to (plan, interval)."""
    if not price_id:
        return None, None
    for key, value in _price_map().items():
        if value and value == price_id:
            plan, interval = key.split("_", 1)
            return plan, interval
    return None, None


def _expires_at(now: datetime, interval: str | None) -> datetime:
    """Compute the plan expiry from an interval (defaults to monthly)."""
    days = _INTERVAL_DAYS.get(interval or "monthly", 30)
    return now + timedelta(days=days)


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------
class CheckoutRequest(BaseModel):
    plan: str       # 'starter' | 'business'
    interval: str   # 'monthly' | 'quarterly' | 'yearly'


class BuyCreditsRequest(BaseModel):
    package: str    # 'losse_scan' | 'starter' | 'groei' | 'pro' | 'expert'


# ---------------------------------------------------------------------------
# 1) Create a Stripe Checkout session
# ---------------------------------------------------------------------------
@router.post("/checkout")
async def create_checkout(
    body: CheckoutRequest,
    user: User = Depends(get_required_user),
):
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED)

    price_id = _price_map().get(f"{body.plan}_{body.interval}", "")
    if not price_id:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED)

    try:
        import stripe

        stripe.api_key = key
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer_email=user.email,
            line_items=[{"price": price_id, "quantity": 1}],
            success_url="https://app.scanix.nl/dashboard?payment=success",
            cancel_url="https://scanix.nl/prijzen",
            metadata={
                "user_id": str(user.id),
                "plan": body.plan,
                "interval": body.interval,
            },
            subscription_data={
                "metadata": {
                    "user_id": str(user.id),
                    "plan": body.plan,
                    "interval": body.interval,
                }
            },
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Stripe checkout session creation failed")
        raise HTTPException(
            status_code=503,
            detail="Er ging iets mis bij het starten van de betaling. Probeer het later opnieuw.",
        )

    return {"checkout_url": session.url}


# ---------------------------------------------------------------------------
# 1b) Credits — one-time purchase via Stripe hosted Checkout (mode=payment)
# ---------------------------------------------------------------------------
@router.post("/buy-credits")
async def buy_credits(
    body: BuyCreditsRequest,
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    pkg = CREDIT_PACKAGES.get(body.package)
    if not pkg:
        raise HTTPException(status_code=400, detail="Onbekend creditpakket")

    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED)

    meta = {
        "type": "credits",
        "user_id": str(user.id),
        "package": body.package,
        "credits": str(pkg["credits"]),
    }

    try:
        import stripe

        stripe.api_key = key

        # Ensure the user has a Stripe customer so iDEAL/card details and
        # purchase history stay attached to one customer record.
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer.id
            await db.commit()

        euros = pkg["price"] // 100
        session = stripe.checkout.Session.create(
            mode="payment",
            customer=user.stripe_customer_id,
            payment_method_types=["card", "ideal"],  # iDEAL for the NL market
            line_items=[
                {
                    "price_data": {
                        "currency": "eur",
                        "product_data": {
                            "name": f"Scanix {pkg['label']} — {pkg['credits']} scan credits",
                            "description": f"€{euros} eenmalig. Credits verlopen nooit.",
                        },
                        "unit_amount": pkg["price"],
                    },
                    "quantity": 1,
                }
            ],
            success_url=f"{_APP_URL}/billing?success=true&package={body.package}",
            cancel_url=f"{_APP_URL}/billing?cancelled=true",
            metadata=meta,
            # Mirror metadata onto the PaymentIntent so payment_intent.succeeded
            # carries it too (idempotency keys off the PaymentIntent id).
            payment_intent_data={"metadata": meta},
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Stripe credits checkout session creation failed")
        raise HTTPException(
            status_code=503,
            detail="Er ging iets mis bij het starten van de betaling. Probeer het later opnieuw.",
        )

    return {"checkout_url": session.url, "amount": pkg["price"]}


# ---------------------------------------------------------------------------
# 1c) Credits — current balance
# ---------------------------------------------------------------------------
@router.get("/credits-balance")
async def credits_balance(
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    balance = await credits_service.get_balance(db, user.id)
    return {**balance, "packages": packages_payload()}


# ---------------------------------------------------------------------------
# 1d) Credits — purchase history (last 20)
# ---------------------------------------------------------------------------
@router.get("/credits-history")
async def credit_history(
    user: User = Depends(get_required_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ScanCredit)
        .where(ScanCredit.user_id == user.id)
        .order_by(ScanCredit.created_at.desc())
        .limit(20)
    )
    rows = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "package_name": r.package_name,
            "credits_purchased": r.credits_purchased,
            "price_paid": r.price_paid,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "status": "paid" if r.price_paid > 0 else "gratis",
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# 2) Stripe webhook (no auth)
# ---------------------------------------------------------------------------
@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if secret:
        try:
            import stripe

            event = stripe.Webhook.construct_event(payload, sig, secret)
        except HTTPException:
            raise
        except Exception:
            logger.warning("Stripe webhook signature verification failed")
            raise HTTPException(status_code=400, detail="Invalid signature")
    else:
        # Dev mode: no secret configured, accept the raw JSON.
        try:
            event = json.loads(payload)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid payload")

    event_type = event.get("type")
    data_object = (event.get("data") or {}).get("object") or {}

    try:
        if event_type == "checkout.session.completed":
            # Credits checkout (mode=payment) vs subscription checkout.
            if (data_object.get("metadata") or {}).get("type") == "credits":
                await _handle_credit_purchase(
                    db,
                    metadata=data_object.get("metadata") or {},
                    payment_intent_id=data_object.get("payment_intent"),
                )
            else:
                await _handle_checkout_completed(db, data_object)
        elif event_type == "payment_intent.succeeded":
            await _handle_credit_purchase(
                db,
                metadata=data_object.get("metadata") or {},
                payment_intent_id=data_object.get("id"),
            )
        elif event_type == "customer.subscription.deleted":
            await _handle_subscription_deleted(db, data_object)
        elif event_type == "invoice.payment_failed":
            await _handle_payment_failed(db, data_object)
        # Any other event type is acknowledged but ignored.
    except Exception:
        # Never leak a 500 back to Stripe for handling errors; log and ack.
        logger.exception("Error while handling Stripe webhook event %s", event_type)

    return {"received": True}


async def _handle_checkout_completed(db: AsyncSession, session: dict) -> None:
    metadata = session.get("metadata") or {}
    user_id = metadata.get("user_id")
    if not user_id:
        logger.warning("checkout.session.completed without user_id in metadata")
        return

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        logger.warning("checkout.session.completed for unknown user_id=%s", user_id)
        return

    plan = metadata.get("plan")
    interval = metadata.get("interval")

    # Fallback: derive plan/interval from the subscription's price id.
    if not plan or not interval:
        price_id = _extract_price_id(session)
        rp, ri = _plan_interval_from_price_id(price_id)
        plan = plan or rp
        interval = interval or ri

    if not plan:
        logger.warning("Could not determine plan for user_id=%s; skipping", user_id)
        return

    now = datetime.now(timezone.utc)
    apply_plan_limits(user, plan)
    user.plan_interval = interval
    user.plan_started_at = now
    user.plan_expires_at = _expires_at(now, interval)
    user.stripe_customer_id = session.get("customer")
    user.stripe_subscription_id = session.get("subscription")
    user.is_active = True
    await db.commit()

    # Best-effort welcome e-mail; the function may not exist yet.
    try:
        from app.services.email import send_welcome_email

        send_welcome_email(user, plan, interval)
    except Exception:
        logger.debug("send_welcome_email unavailable or failed", exc_info=True)


async def _handle_credit_purchase(db: AsyncSession, *, metadata: dict, payment_intent_id) -> None:
    """Grant credits for a one-time payment. Idempotent on the PaymentIntent id,
    so duplicate webhook deliveries (e.g. both checkout.session.completed and
    payment_intent.succeeded) only ever add credits once."""
    if not metadata or metadata.get("type") != "credits":
        return

    user_id = metadata.get("user_id")
    package = metadata.get("package")
    if not user_id or not package or package not in CREDIT_PACKAGES:
        logger.warning("credit purchase with bad metadata: %s", metadata)
        return
    if not payment_intent_id:
        logger.warning("credit purchase without payment_intent id; metadata=%s", metadata)
        return

    try:
        uid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        logger.warning("credit purchase with invalid user_id=%s", user_id)
        return

    pkg = CREDIT_PACKAGES[package]
    record = await credits_service.add_credits(
        db,
        user_id=uid,
        amount=pkg["credits"],
        package_name=package,
        price_paid=pkg["price"],
        stripe_payment_id=str(payment_intent_id),
    )
    if record is None:
        logger.info("credit purchase already processed (pi=%s)", payment_intent_id)
        return

    # Best-effort confirmation e-mail (function may not exist yet).
    try:
        from app.services.email import send_credits_purchased

        send_credits_purchased(uid, pkg["credits"], pkg["label"])
    except Exception:
        logger.debug("send_credits_purchased unavailable or failed", exc_info=True)


async def _handle_subscription_deleted(db: AsyncSession, subscription: dict) -> None:
    sub_id = subscription.get("id")
    customer = subscription.get("customer")

    user = None
    if sub_id:
        result = await db.execute(
            select(User).where(User.stripe_subscription_id == sub_id)
        )
        user = result.scalar_one_or_none()
    if not user and customer:
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer)
        )
        user = result.scalar_one_or_none()

    if not user:
        logger.warning(
            "customer.subscription.deleted for unknown sub=%s customer=%s",
            sub_id,
            customer,
        )
        return

    apply_plan_limits(user, "trial")
    user.plan_interval = None
    await db.commit()

    try:
        from app.services.email import send_subscription_ended

        send_subscription_ended(user)
    except Exception:
        logger.debug("send_subscription_ended unavailable or failed", exc_info=True)


async def _handle_payment_failed(db: AsyncSession, invoice: dict) -> None:
    customer = invoice.get("customer")
    logger.warning("invoice.payment_failed for customer=%s", customer)

    # Do not change the plan; only attempt a best-effort notification.
    user = None
    if customer:
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer)
        )
        user = result.scalar_one_or_none()

    if user:
        try:
            from app.services.email import send_payment_failed

            send_payment_failed(user)
        except Exception:
            logger.debug("send_payment_failed unavailable or failed", exc_info=True)


def _extract_price_id(session: dict) -> str | None:
    """Best-effort extraction of a price id from a checkout session object."""
    try:
        line_items = session.get("line_items") or {}
        data = line_items.get("data") or []
        if data:
            price = data[0].get("price") or {}
            return price.get("id")
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# 3) Stripe billing portal
# ---------------------------------------------------------------------------
@router.get("/portal")
async def billing_portal(
    user: User = Depends(get_required_user),
):
    key = os.getenv("STRIPE_SECRET_KEY")
    if not key:
        raise HTTPException(status_code=503, detail=_NOT_CONFIGURED)

    if not user.stripe_customer_id:
        raise HTTPException(status_code=404, detail="Geen abonnement gevonden")

    try:
        import stripe

        stripe.api_key = key
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url="https://app.scanix.nl/billing",
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Stripe billing portal session creation failed")
        raise HTTPException(
            status_code=503,
            detail="Er ging iets mis bij het openen van het klantportaal. Probeer het later opnieuw.",
        )

    return {"portal_url": session.url}
