"""User model — synced from Clerk via webhook."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clerk_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255))

    # Subscription
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), unique=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan: Mapped[str] = mapped_column(String(50), default="free")  # free, starter, professional, business
    credits: Mapped[int] = mapped_column(Integer, default=0)
    max_concurrent_scans: Mapped[int] = mapped_column(Integer, default=1)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Real authentication + commercial fields (migration 0003)
    name: Mapped[str | None] = mapped_column(String(255))
    company_name: Mapped[str | None] = mapped_column(String(255))
    password_hash: Mapped[str | None] = mapped_column(String(255))
    api_key: Mapped[str | None] = mapped_column(String(255), index=True)
    terms_accepted: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terms_version: Mapped[str | None] = mapped_column(String(20))
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    notify_on_complete: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    notification_email: Mapped[str | None] = mapped_column(String(320))

    # AI analysis provider preference (migration 0004 + 0005)
    ai_provider: Mapped[str] = mapped_column(String(20), server_default="deepseek", default="deepseek")  # deepseek | anthropic | runpod
    ai_provider_active: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)  # paid upgrade active
    ai_api_key: Mapped[str | None] = mapped_column(String(255))   # legacy: user's own key (local)
    ai_base_url: Mapped[str | None] = mapped_column(String(255))  # legacy: self-hosted base URL

    # Commercial plan system (migration 0007)
    plan_interval: Mapped[str | None] = mapped_column(String(20))   # monthly | quarterly | yearly
    plan_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    plan_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    max_targets: Mapped[int] = mapped_column(Integer, server_default="1", default=1)
    max_scans_per_month: Mapped[int] = mapped_column(Integer, server_default="3", default=3)
    scans_this_month: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    scans_reset_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    custom_modules: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    scheduled_scans: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    white_label: Mapped[bool] = mapped_column(Boolean, server_default="false", default=False)
    ai_upgrade: Mapped[str] = mapped_column(String(20), server_default="deepseek", default="deepseek")  # deepseek | choice
    role: Mapped[str] = mapped_column(String(20), server_default="user", default="user")  # user | admin
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    targets = relationship("Target", back_populates="user", cascade="all, delete-orphan")
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    nda_acceptances = relationship("NDAAcceptance", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
