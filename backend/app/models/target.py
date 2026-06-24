"""Target model — domains/IPs that a user has registered for scanning."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Target(Base):
    __tablename__ = "targets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Target definition
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)  # domain, ip, ip_range, url
    value: Mapped[str] = mapped_column(String(500), nullable=False)  # the actual domain/IP/range

    # Scope definition
    scope: Mapped[dict | None] = mapped_column(JSONB, default=dict)
    # Example: {"ports": [80, 443, 8080], "paths": ["/api", "/admin"], "exclude": ["192.168.1.5"]}

    # Multi-target scanning (migration 0009) — CIDR / IP range / discovered hosts.
    cidr_notation: Mapped[str | None] = mapped_column(String(64))
    ip_range_start: Mapped[str | None] = mapped_column(String(64))
    ip_range_end: Mapped[str | None] = mapped_column(String(64))
    discovered_hosts: Mapped[list | None] = mapped_column(JSONB)
    parent_target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("targets.id", ondelete="CASCADE"), nullable=True
    )

    # Verification
    verification_method: Mapped[str | None] = mapped_column(String(50))  # dns_txt, file_upload, legal_declaration
    verification_token: Mapped[str | None] = mapped_column(String(255))
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="targets")
    scans = relationship("Scan", back_populates="target", cascade="all, delete-orphan")
