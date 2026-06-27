"""DemoScan — public, unauthenticated demo scan against scanme.nmap.org (0014)."""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Text, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class DemoScan(Base):
    __tablename__ = "demo_scans"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ip_address: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending")  # pending|running|completed|failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    terminal_output: Mapped[str | None] = mapped_column(Text)
    findings: Mapped[list] = mapped_column(JSONB, default=list)
    ws_token: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
