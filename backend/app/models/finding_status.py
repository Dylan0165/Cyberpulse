"""FindingStatus — per-finding triage state (migration 0012).

Findings live as JSONB on scans.findings. This table records an override status
(open / resolved / false_positive / accepted_risk) keyed by a stable finding_id
the scan pipeline assigns, so triage survives without rewriting the JSONB blob.
"""

import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

VALID_STATUSES = ("open", "resolved", "false_positive", "accepted_risk")


class FindingStatus(Base):
    __tablename__ = "finding_statuses"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    finding_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    scan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("scans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="open")
    status_note: Mapped[str | None] = mapped_column(String(1000))
    status_set_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status_set_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
