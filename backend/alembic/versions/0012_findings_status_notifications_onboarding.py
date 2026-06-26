"""Finding status table + user notification prefs + onboarding flags.

ADDITIVE + idempotent. Adds:
  - users.notify_* (email preferences), users.onboarding_* (wizard state)
  - finding_statuses table (per-finding open/resolved/false_positive/accepted_risk)

Findings themselves stay as JSONB on scans.findings (no breaking change to the
scan pipeline); per-finding status is tracked in finding_statuses keyed by a
stable finding_id the pipeline assigns.

Revision ID: 0012
Revises: 0011
Create Date: 2026-06-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0012"
down_revision: Union[str, None] = "0011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


_USER_COLUMNS = [
    ("notify_scan_complete", sa.Column("notify_scan_complete", sa.Boolean(), server_default=sa.true(), nullable=False)),
    ("notify_critical_only", sa.Column("notify_critical_only", sa.Boolean(), server_default=sa.false(), nullable=False)),
    ("notify_scheduled_fail", sa.Column("notify_scheduled_fail", sa.Boolean(), server_default=sa.true(), nullable=False)),
    ("onboarding_completed", sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.false(), nullable=False)),
    ("onboarding_step", sa.Column("onboarding_step", sa.Integer(), server_default="0", nullable=False)),
]


def upgrade() -> None:
    for name, col in _USER_COLUMNS:
        if not _has_column("users", name):
            op.add_column("users", col)

    if not _has_table("finding_statuses"):
        op.create_table(
            "finding_statuses",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("finding_id", sa.String(64), nullable=False, unique=True),
            sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="open"),
            sa.Column("status_note", sa.String(1000), nullable=True),
            sa.Column("status_set_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("status_set_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_finding_statuses_scan_id", "finding_statuses", ["scan_id"])


def downgrade() -> None:
    if _has_table("finding_statuses"):
        op.drop_table("finding_statuses")
    for name, _ in reversed(_USER_COLUMNS):
        if _has_column("users", name):
            op.drop_column("users", name)
