"""Prepaid credits system: per-scan credits replace monthly subscription quota.

ADDITIVE + idempotent on purpose. Per the backward-compat rule (feature flag
USE_CREDITS_MODEL), the legacy subscription columns (plan_interval,
plan_expires_at, max_scans_per_month, scans_this_month) are intentionally LEFT
IN PLACE so the existing subscription code keeps working when the flag is off.
0008 only adds the new credits columns + tables and migrates existing users
onto a credits balance. downgrade() drops only what this revision added.

Revision ID: 0008
Revises: 0007
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return insp.has_table(table)


_USER_COLUMNS = [
    ("credits_remaining", sa.Column("credits_remaining", sa.Integer(), server_default="0", nullable=False)),
    ("credits_total", sa.Column("credits_total", sa.Integer(), server_default="0", nullable=False)),
]


def upgrade() -> None:
    # 1) New balance columns on users (additive).
    for name, col in _USER_COLUMNS:
        if not _has_column("users", name):
            op.add_column("users", col)

    # plan already exists; make 'credits' the new default for fresh rows.
    op.alter_column(
        "users",
        "plan",
        existing_type=sa.String(50),
        server_default="credits",
        existing_nullable=True,
    )

    # 2) scan_credits — one row per purchase (Stripe one-time / trial / admin).
    if not _has_table("scan_credits"):
        op.create_table(
            "scan_credits",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("package_name", sa.String(50), nullable=False),
            sa.Column("credits_purchased", sa.Integer(), nullable=False),
            sa.Column("price_paid", sa.Integer(), nullable=False),  # eurocents
            sa.Column("stripe_payment_id", sa.String(255), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_scan_credits_user_id", "scan_credits", ["user_id"])

    # 3) credit_usage — one row per credit spent on a scan.
    if not _has_table("credit_usage"):
        op.create_table(
            "credit_usage",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("scan_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("scans.id", ondelete="CASCADE"), nullable=False),
            sa.Column("credits_used", sa.Integer(), server_default="1", nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_credit_usage_user_id", "credit_usage", ["user_id"])
        op.create_index("ix_credit_usage_scan_id", "credit_usage", ["scan_id"])

    # 4) Migrate existing users onto a credits balance.
    #    trial/starter -> 1 credit on the trial plan; paid subscriptions -> unlimited.
    op.execute(
        """
        UPDATE users
        SET plan = 'business', credits_remaining = 999999
        WHERE plan = 'business'
        """
    )
    op.execute(
        """
        UPDATE users
        SET plan = 'enterprise', credits_remaining = 999999
        WHERE plan = 'enterprise'
        """
    )
    op.execute(
        """
        UPDATE users
        SET plan = 'trial', credits_remaining = 1
        WHERE plan IS NULL OR plan IN ('trial', 'starter', 'free', 'professional')
        """
    )
    # credits_total mirrors any granted balance for already-migrated users.
    op.execute(
        """
        UPDATE users
        SET credits_total = credits_remaining
        WHERE credits_total = 0 AND credits_remaining > 0 AND credits_remaining < 999999
        """
    )


def downgrade() -> None:
    if _has_table("credit_usage"):
        op.drop_table("credit_usage")
    if _has_table("scan_credits"):
        op.drop_table("scan_credits")

    op.alter_column(
        "users",
        "plan",
        existing_type=sa.String(50),
        server_default="free",
        existing_nullable=True,
    )
    for name, _ in reversed(_USER_COLUMNS):
        if _has_column("users", name):
            op.drop_column("users", name)
