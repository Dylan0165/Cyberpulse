"""Pydantic schemas for user accounts and billing."""

from datetime import datetime
from uuid import UUID
from pydantic import BaseModel


class UserResponse(BaseModel):
    id: UUID
    clerk_id: str
    email: str
    full_name: str | None
    company: str | None
    plan: str
    credits: int
    max_concurrent_scans: int
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class BillingInfo(BaseModel):
    plan: str
    credits: int
    stripe_customer_id: str | None
    subscription_status: str | None


class CreateCheckoutRequest(BaseModel):
    price_id: str
    success_url: str
    cancel_url: str


class PurchaseCreditsRequest(BaseModel):
    quantity: int  # Number of credits to purchase


class WebhookEvent(BaseModel):
    type: str
    data: dict
