"""Stripe billing service — subscriptions, credits, checkout, and webhooks."""

import logging
from typing import Optional

import stripe
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

stripe.api_key = settings.stripe_secret_key

# ──────────────────────────────────────────────────────────────
# Plan configuration
# ──────────────────────────────────────────────────────────────
PLANS = {
    "starter": {
        "price_id": settings.stripe_starter_price_id,
        "credits_per_month": 5,
        "max_concurrent_scans": 1,
        "max_domains": 3,
        "price_eur": 99,
        "features": ["quick_scan"],
    },
    "professional": {
        "price_id": settings.stripe_professional_price_id,
        "credits_per_month": 20,
        "max_concurrent_scans": 3,
        "max_domains": 15,
        "price_eur": 299,
        "features": ["quick_scan", "full_scan", "scheduling"],
    },
    "business": {
        "price_id": settings.stripe_business_price_id,
        "credits_per_month": 999,
        "max_concurrent_scans": 10,
        "max_domains": 999,
        "price_eur": 799,
        "features": ["quick_scan", "full_scan", "scheduling", "white_label", "api_access"],
    },
}

# Credit add-on bundles: (quantity, price_eur)
CREDIT_BUNDLES = [
    (5, 49),
    (15, 129),
    (50, 399),
]

SCAN_CREDIT_COST = {
    "quick": 1,
    "full": 5,
    "custom": 3,
}

# Lazy sync engine for webhook handler (created on first use)
_sync_engine = None


def _get_db_session() -> Session:
    global _sync_engine
    if _sync_engine is None:
        _sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)
    return Session(_sync_engine)


# ──────────────────────────────────────────────────────────────
# Customer helpers
# ──────────────────────────────────────────────────────────────

async def create_customer(email: str, name: Optional[str] = None, metadata: Optional[dict] = None) -> str:
    """Create a Stripe customer and return their ID."""
    customer = stripe.Customer.create(
        email=email,
        name=name,
        metadata=metadata or {},
    )
    return customer.id


# ──────────────────────────────────────────────────────────────
# Checkout
# ──────────────────────────────────────────────────────────────

async def create_checkout_session(
    user_id: str,
    plan: str,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a Stripe Checkout session for the given plan and return the URL.

    Looks up or creates the Stripe customer from the DB user record.
    """
    if plan not in PLANS:
        raise ValueError(f"Unknown plan: {plan}")

    price_id = PLANS[plan]["price_id"]
    if not price_id:
        raise ValueError(f"No Stripe price ID configured for plan: {plan}")

    # Get or create Stripe customer
    from app.models.user import User
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError(f"User {user_id} not found")
        customer_id = user.stripe_customer_id
        if not customer_id:
            customer_id = await create_customer(
                email=user.email,
                name=user.full_name,
                metadata={"user_id": str(user_id), "clerk_id": user.clerk_id},
            )
            user.stripe_customer_id = customer_id
            db.commit()

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card", "ideal", "bancontact"],
        line_items=[{"price": price_id, "quantity": 1}],
        mode="subscription",
        success_url=success_url,
        cancel_url=cancel_url,
        allow_promotion_codes=True,
        metadata={"user_id": str(user_id), "plan": plan},
    )
    return session.url


async def create_credit_checkout(
    user_id: str,
    credits: int,
    success_url: str,
    cancel_url: str,
) -> str:
    """Create a one-time payment session for purchasing scan credits."""
    # Find appropriate bundle price
    bundle_price = None
    for qty, _price in CREDIT_BUNDLES:
        if credits == qty:
            bundle_price = settings.stripe_single_scan_price_id  # reuse single price
            break

    if not bundle_price:
        bundle_price = settings.stripe_single_scan_price_id

    from app.models.user import User
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            raise ValueError("User not found")
        customer_id = user.stripe_customer_id

    session = stripe.checkout.Session.create(
        customer=customer_id,
        payment_method_types=["card", "ideal"],
        line_items=[{"price": bundle_price, "quantity": credits}],
        mode="payment",
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={"user_id": str(user_id), "credits": str(credits)},
    )
    return session.url


# ──────────────────────────────────────────────────────────────
# Credits
# ──────────────────────────────────────────────────────────────

def add_credits(user_id: str, credits: int) -> None:
    """Add scan credits to a user account (synchronous — called from webhooks)."""
    from app.models.user import User
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.credits = (user.credits or 0) + credits
            db.commit()
            logger.info("Added %d credits to user %s (total: %d)", credits, user_id, user.credits)


def deduct_credit(user_id: str, scan_type: str = "quick") -> bool:
    """Deduct one scan credit. Returns False if user has no credits."""
    from app.models.user import User
    cost = SCAN_CREDIT_COST.get(scan_type, 1)
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or user.credits < cost:
            return False
        user.credits -= cost
        db.commit()
        return True


# ──────────────────────────────────────────────────────────────
# Customer portal
# ──────────────────────────────────────────────────────────────

async def get_billing_portal_url(user_id: str, return_url: str) -> str:
    """Create a Stripe Customer Portal session and return the URL."""
    from app.models.user import User
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.stripe_customer_id:
            raise ValueError("User has no Stripe customer ID")
        customer_id = user.stripe_customer_id

    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url


async def cancel_subscription(user_id: str) -> bool:
    """Cancel subscription at end of current period."""
    from app.models.user import User
    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None or not user.stripe_subscription_id:
            return False
        try:
            stripe.Subscription.modify(user.stripe_subscription_id, cancel_at_period_end=True)
            return True
        except stripe.error.StripeError as e:
            logger.error("Failed to cancel subscription for %s: %s", user_id, e)
            return False


# ──────────────────────────────────────────────────────────────
# Webhook handler
# ──────────────────────────────────────────────────────────────

def verify_webhook_signature(payload: bytes, sig_header: str) -> dict:
    """Verify and parse a Stripe webhook event. Raises on invalid signature."""
    return stripe.Webhook.construct_event(
        payload, sig_header, settings.stripe_webhook_secret
    )


def handle_webhook(event: dict) -> None:
    """Process a verified Stripe webhook event.

    Supported events:
    - checkout.session.completed → assign plan + credits
    - invoice.paid → refresh monthly credits
    - invoice.payment_failed → downgrade to free
    - customer.subscription.deleted → reset to free
    - charge.refunded → deduct credits (optional)
    """
    from app.models.user import User

    event_type = event["type"]
    data = event["data"]["object"]
    logger.info("Stripe webhook: %s", event_type)

    if event_type == "checkout.session.completed":
        _handle_checkout_completed(data)

    elif event_type == "invoice.paid":
        _handle_invoice_paid(data)

    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(data)

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(data)


def _handle_checkout_completed(session: dict) -> None:
    """Assign plan and credits after successful checkout."""
    from app.models.user import User

    user_id = session.get("metadata", {}).get("user_id")
    plan = session.get("metadata", {}).get("plan")
    credits_str = session.get("metadata", {}).get("credits")

    if not user_id:
        logger.warning("checkout.session.completed missing user_id in metadata")
        return

    with _get_db_session() as db:
        user = db.query(User).filter(User.id == user_id).first()
        if user is None:
            logger.error("User %s not found for checkout event", user_id)
            return

        # Update customer ID if not yet stored
        customer_id = session.get("customer")
        if customer_id and not user.stripe_customer_id:
            user.stripe_customer_id = customer_id

        subscription_id = session.get("subscription")
        if subscription_id:
            user.stripe_subscription_id = subscription_id

        if plan and plan in PLANS:
            # Subscription upgrade
            plan_cfg = PLANS[plan]
            user.plan = plan
            user.credits = plan_cfg["credits_per_month"]
            user.max_concurrent_scans = plan_cfg["max_concurrent_scans"]
            logger.info("User %s upgraded to %s plan with %d credits", user_id, plan, user.credits)

        elif credits_str:
            # One-time credit purchase
            try:
                credits = int(credits_str)
                user.credits = (user.credits or 0) + credits
                logger.info("User %s purchased %d credits (total: %d)", user_id, credits, user.credits)
            except (ValueError, TypeError):
                pass

        db.commit()


def _handle_invoice_paid(invoice: dict) -> None:
    """Refresh monthly credits on successful invoice payment (subscription renewal)."""
    from app.models.user import User

    customer_id = invoice.get("customer")
    if not customer_id:
        return

    with _get_db_session() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user is None:
            return

        plan_cfg = PLANS.get(user.plan)
        if plan_cfg:
            user.credits = plan_cfg["credits_per_month"]
            db.commit()
            logger.info("Monthly credits refreshed for user %s: %d", user.id, user.credits)


def _handle_payment_failed(invoice: dict) -> None:
    """Downgrade user to free plan on payment failure."""
    from app.models.user import User

    customer_id = invoice.get("customer")
    if not customer_id:
        return

    with _get_db_session() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.plan = "free"
            user.credits = max(user.credits, 0)  # don't remove already-bought credits
            user.max_concurrent_scans = 1
            db.commit()
            logger.warning("Payment failed — downgraded user %s to free plan", user.id)


def _handle_subscription_deleted(subscription: dict) -> None:
    """Reset user to free plan when subscription is cancelled/deleted."""
    from app.models.user import User

    customer_id = subscription.get("customer")
    if not customer_id:
        return

    with _get_db_session() as db:
        user = db.query(User).filter(User.stripe_customer_id == customer_id).first()
        if user:
            user.plan = "free"
            user.stripe_subscription_id = None
            user.max_concurrent_scans = 1
            db.commit()
            logger.info("Subscription cancelled — user %s reset to free plan", user.id)
