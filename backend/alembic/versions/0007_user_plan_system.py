"""Commercial plan system: plan limits, billing + role fields on users.

Additive + idempotent. Existing users are moved to the 'trial' plan with trial
limits; their scans/targets remain accessible.

Revision ID: 0007
Revises: 0006
Create Date: 2026-06-18 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


_COLUMNS = [
    ("plan_interval", sa.Column("plan_interval", sa.String(20), nullable=True)),
    ("plan_started_at", sa.Column("plan_started_at", sa.DateTime(timezone=True), nullable=True)),
    ("plan_expires_at", sa.Column("plan_expires_at", sa.DateTime(timezone=True), nullable=True)),
    ("max_targets", sa.Column("max_targets", sa.Integer(), server_default="1", nullable=False)),
    ("max_scans_per_month", sa.Column("max_scans_per_month", sa.Integer(), server_default="3", nullable=False)),
    ("scans_this_month", sa.Column("scans_this_month", sa.Integer(), server_default="0", nullable=False)),
    ("scans_reset_at", sa.Column("scans_reset_at", sa.DateTime(timezone=True), nullable=True)),
    ("custom_modules", sa.Column("custom_modules", sa.Boolean(), server_default="false", nullable=False)),
    ("scheduled_scans", sa.Column("scheduled_scans", sa.Boolean(), server_default="false", nullable=False)),
    ("white_label", sa.Column("white_label", sa.Boolean(), server_default="false", nullable=False)),
    ("ai_upgrade", sa.Column("ai_upgrade", sa.String(20), server_default="deepseek", nullable=False)),
    ("role", sa.Column("role", sa.String(20), server_default="user", nullable=False)),
    ("last_login_at", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True)),
]


def upgrade() -> None:
    for name, col in _COLUMNS:
        if not _has_column("users", name):
            op.add_column("users", col)

    # Move legacy users (free/professional/None) onto the trial plan with trial
    # limits. Already-commercial plans are left untouched, so this is re-runnable.
    op.execute(
        """
        UPDATE users
        SET plan = 'trial',
            max_targets = 1,
            max_scans_per_month = 1,
            custom_modules = false,
            scheduled_scans = false,
            white_label = false,
            ai_upgrade = 'deepseek'
        WHERE plan IS NULL OR plan IN ('free', 'professional', 'starter_old')
        """
    )


def downgrade() -> None:
    for name, _ in reversed(_COLUMNS):
        if _has_column("users", name):
            op.drop_column("users", name)
