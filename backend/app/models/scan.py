"""Scan model — metadata for each penetration test run."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Boolean, Float, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Scan(Base):
    __tablename__ = "scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("targets.id"), nullable=False)

    # Scan configuration
    scan_type: Mapped[str] = mapped_column(String(50), nullable=False)  # quick, full, custom
    phases: Mapped[list] = mapped_column(JSONB, default=list)
    # ["recon", "vulnerability", "webapp", "network", "auth", "ssl", "cloud", "osint"]
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending -> nda_required -> verified -> running -> analyzing -> completed / failed / cancelled
    current_phase: Mapped[str | None] = mapped_column(String(50))
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100

    # Results (only stored if user opted in)
    save_report: Mapped[bool] = mapped_column(Boolean, default=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)  # AI-analyzed report (if saved)
    security_score: Mapped[float | None] = mapped_column(Float)  # 0-100

    # Finding counts
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)

    # Container tracking
    container_id: Mapped[str | None] = mapped_column(String(100))

    # NDA reference
    nda_acceptance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nda_acceptances.id"))

    # Credits consumed
    credits_used: Mapped[int] = mapped_column(Integer, default=0)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(50))  # weekly, monthly

    # Timestamps
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Shareable link
    share_token: Mapped[str | None] = mapped_column(String(64), unique=True)
    share_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    user = relationship("User", back_populates="scans")
    target = relationship("Target", back_populates="scans")
    nda_acceptance = relationship("NDAAcceptance")
