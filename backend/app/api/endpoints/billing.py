"""Billing and subscription endpoints — Stripe integration."""

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.auth import get_current_user, get_client_ip
from app.models.user import User
from app.schemas.user import BillingInfo, CreateCheckoutRequest, PurchaseCreditsRequest
from app.services.billing import (
    create_customer,
    create_checkout_session,
    create_credit_checkout,
    get_subscription,
    cancel_subscription,
    verify_webhook_signature,
    PLANS,
)
from app.services.audit import log_action
from app.core.config import get_settings

router = APIRouter(prefix="/billing", tags=["billing"])
settings = get_settings()


async def _get_user(db: AsyncSession, clerk_id: str) -> User:
    result = await db.execute(select(User).where(User.clerk_id == clerk_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/info", response_model=BillingInfo)
async def get_billing_info(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    sub_status = None
    if user.stripe_subscription_id:
        sub = await get_subscription(user.stripe_subscription_id)
        sub_status = sub.get("status") if sub else None

    return BillingInfo(
        plan=user.plan,
        credits=user.credits,
        stripe_customer_id=user.stripe_customer_id,
        subscription_status=sub_status,
    )


@router.post("/checkout")
async def create_checkout(
    body: CreateCheckoutRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    # Ensure Stripe customer exists
    if not user.stripe_customer_id:
        customer_id = await create_customer(
            email=user.email,
            name=user.full_name,
            metadata={"clerk_id": user.clerk_id},
        )
        user.stripe_customer_id = customer_id
        await db.commit()

    url = await create_checkout_session(
        customer_id=user.stripe_customer_id,
        price_id=body.price_id,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
    )

    return {"checkout_url": url}


@router.post("/purchase-credits")
async def purchase_credits(
    body: PurchaseCreditsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    if body.quantity < 1 or body.quantity > 100:
        raise HTTPException(status_code=400, detail="Quantity must be between 1 and 100")

    if not user.stripe_customer_id:
        customer_id = await create_customer(
            email=user.email,
            name=user.full_name,
            metadata={"clerk_id": user.clerk_id},
        )
        user.stripe_customer_id = customer_id
        await db.commit()

    url = await create_credit_checkout(
        customer_id=user.stripe_customer_id,
        quantity=body.quantity,
        success_url=f"{settings.frontend_url}/billing?success=true",
        cancel_url=f"{settings.frontend_url}/billing?cancelled=true",
    )

    return {"checkout_url": url}


@router.post("/cancel-subscription")
async def cancel_sub(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user = await _get_user(db, current_user["clerk_id"])

    if not user.stripe_subscription_id:
        raise HTTPException(status_code=400, detail="No active subscription")

    success = await cancel_subscription(user.stripe_subscription_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel subscription")

    ip = await get_client_ip(request)
    await log_action(
        db, "subscription_cancelled", ip, user_id=user.id,
        resource_type="subscription", resource_id=user.stripe_subscription_id,
    )

    return {"message": "Subscription will be cancelled at period end"}


@router.post("/webhooks/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")

    try:
        event = verify_webhook_signature(payload, sig_header)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "checkout.session.completed":
        customer_id = data.get("customer")
        mode = data.get("mode")

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            return {"status": "user_not_found"}

        if mode == "subscription":
            subscription_id = data.get("subscription")
            user.stripe_subscription_id = subscription_id

            # Determine plan from price
            line_items = data.get("line_items", {}).get("data", [])
            for item in line_items:
                price_id = item.get("price", {}).get("id")
                for plan_name, plan_config in PLANS.items():
                    if plan_config["price_id"] == price_id:
                        user.plan = plan_name
                        user.credits += plan_config["credits_per_month"]
                        user.max_concurrent_scans = plan_config["max_concurrent_scans"]
                        break

        elif mode == "payment":
            # Credit purchase
            quantity = data.get("amount_total", 0) // 2900  # €29 per credit
            user.credits += max(quantity, 1)

        await db.commit()

    elif event_type == "customer.subscription.updated":
        customer_id = data.get("customer")
        status = data.get("status")

        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user and status == "canceled":
            user.plan = "free"
            user.max_concurrent_scans = 1
            await db.commit()

    elif event_type == "invoice.paid":
        customer_id = data.get("customer")
        result = await db.execute(
            select(User).where(User.stripe_customer_id == customer_id)
        )
        user = result.scalar_one_or_none()
        if user:
            plan_config = PLANS.get(user.plan, {})
            user.credits += plan_config.get("credits_per_month", 0)
            await db.commit()

    return {"status": "ok"}
