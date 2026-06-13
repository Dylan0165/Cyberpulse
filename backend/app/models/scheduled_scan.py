"""ScheduledScan model — recurring automated scans."""

import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Boolean, Integer, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScheduledScan(Base):
    __tablename__ = "scheduled_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    target_ip: Mapped[str] = mapped_column(String(500), nullable=False)
    target_name: Mapped[str | None] = mapped_column(String(255))
    phases: Mapped[list] = mapped_column(JSONB, default=list)
    custom_modules: Mapped[list] = mapped_column(JSONB, default=list)
    schedule_type: Mapped[str] = mapped_column(String(20), default="weekly")  # daily | weekly | monthly

    is_active: Mapped[bool] = mapped_column(Boolean, server_default="true", default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_risk_score: Mapped[int | None] = mapped_column(Integer)
