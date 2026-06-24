"""Prepaid credits models (migration 0008).

scan_credits  — immutable ledger of credit purchases (Stripe one-time, trial
                grant, or admin manual). `stripe_payment_id` is unique so the
                webhook can add credits idempotently.
credit_usage  — immutable ledger of credits spent, one row per scan.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScanCredit(Base):
    __tablename__ = "scan_credits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    package_name: Mapped[str] = mapped_column(String(50), nullable=False)
    credits_purchased: Mapped[int] = mapped_column(Integer, nullable=False)
    price_paid: Mapped[int] = mapped_column(Integer, nullable=False)  # eurocents
    stripe_payment_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class CreditUsage(Base):
    __tablename__ = "credit_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    credits_used: Mapped[int] = mapped_column(Integer, server_default="1", default=1)
    used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
