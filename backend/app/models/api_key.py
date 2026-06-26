"""ApiKey — programmatic access tokens for customers (migration 0013).

Only the SHA-256 hash of the key is stored; the plaintext is shown once on
creation. `key_prefix` is kept for display ("sx_live_abc1…").
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

VALID_SCOPES = ("scan:read", "scan:create", "scan:delete", "report:read", "target:manage")


class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_hash: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    key_prefix: Mapped[str] = mapped_column(String(32), nullable=False)
    scopes: Mapped[list] = mapped_column(JSONB, default=lambda: ["scan:read", "scan:create"])
    last_used: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
