"""MultiScanJob — tracks a fan-out of per-host scans (CIDR / range / subdomain).

One job represents a single user request like "scan 192.168.1.0/24". It holds
the discovery input, progress counters and the list of child scan UUIDs so the
frontend can poll a combined status (migration 0009).
"""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class MultiScanJob(Base):
    __tablename__ = "multi_scan_jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    job_type: Mapped[str] = mapped_column(String(32), nullable=False)  # cidr | range | subdomain
    input: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="discovering")
    # statuses: discovering | scanning | completed | failed
    total_hosts: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    scanned_hosts: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    credits_used: Mapped[int] = mapped_column(Integer, server_default="0", default=0)
    scan_ids: Mapped[list] = mapped_column(JSONB, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
