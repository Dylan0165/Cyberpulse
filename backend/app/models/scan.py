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
    config: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Extended scan context (added in migration 0002)
    scan_mode: Mapped[str] = mapped_column(String(20), server_default="blackbox")
    target_type: Mapped[str] = mapped_column(String(50), server_default="web")
    credentials: Mapped[dict | None] = mapped_column(JSONB)          # username, password, ssh_key, bearer_token
    phases_enabled: Mapped[list | None] = mapped_column(JSONB)        # phases the user opted into
    phases_completed: Mapped[list | None] = mapped_column(JSONB, default=list)
    findings: Mapped[list | None] = mapped_column(JSONB, default=list)
    ai_analysis: Mapped[dict | None] = mapped_column(JSONB)           # DeepSeek structured output
    ai_provider_used: Mapped[str | None] = mapped_column(String(30))  # deepseek | anthropic | runpod
    tool_outputs: Mapped[dict | None] = mapped_column(JSONB, default=dict)  # {phase: {tool: stdout}}
    custom_config: Mapped[dict | None] = mapped_column(JSONB)         # e.g. cloud_credentials (never logged)
    secure_solution_path: Mapped[str | None] = mapped_column(String)  # pre-generated Secure Solution PDF

    # Status tracking
    status: Mapped[str] = mapped_column(String(50), default="pending")
    # pending → nda_required → verified → running → analyzing → completed / failed / cancelled
    current_phase: Mapped[str | None] = mapped_column(String(50))    # phase name
    current_phase_num: Mapped[int] = mapped_column(Integer, default=0)  # phase number 1–8
    progress: Mapped[int] = mapped_column(Integer, default=0)         # 0–100

    # Results
    save_report: Mapped[bool] = mapped_column(Boolean, default=False)
    report_data: Mapped[dict | None] = mapped_column(JSONB)
    security_score: Mapped[float | None] = mapped_column(Float)

    # Finding counts
    critical_count: Mapped[int] = mapped_column(Integer, default=0)
    high_count: Mapped[int] = mapped_column(Integer, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, default=0)
    low_count: Mapped[int] = mapped_column(Integer, default=0)
    info_count: Mapped[int] = mapped_column(Integer, default=0)

    # Container / job tracking (legacy, kept for compat)
    container_id: Mapped[str | None] = mapped_column(String(100))

    # NDA reference
    nda_acceptance_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("nda_acceptances.id"))

    # Credits (unused in school project but kept for compat)
    credits_used: Mapped[int] = mapped_column(Integer, default=0)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_recurring: Mapped[bool] = mapped_column(Boolean, default=False)
    recurrence_pattern: Mapped[str | None] = mapped_column(String(50))

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
