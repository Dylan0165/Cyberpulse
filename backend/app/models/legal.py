"""NDA/RoE acceptance and Audit log models — immutable legal records."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB, INET
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class NDAAcceptance(Base):
    __tablename__ = "nda_acceptances"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("targets.id"), nullable=False)

    # Legal acceptance details
    nda_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    roe_version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    authorization_confirmed: Mapped[bool] = mapped_column(default=False)
    nda_accepted: Mapped[bool] = mapped_column(default=False)

    # Audit fields — immutable after creation
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)
    accepted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # NDA text hash for tamper evidence
    nda_text_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    user = relationship("User", back_populates="nda_acceptances")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Event details
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    # scan_started, scan_completed, scan_failed, nda_accepted, report_viewed,
    # report_exported, target_verified, target_created, user_signed_in, etc.
    resource_type: Mapped[str | None] = mapped_column(String(50))  # scan, target, report, user
    resource_id: Mapped[str | None] = mapped_column(String(100))
    details: Mapped[dict | None] = mapped_column(JSONB)

    # Context
    ip_address: Mapped[str] = mapped_column(String(45), nullable=False)
    user_agent: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="audit_logs")
