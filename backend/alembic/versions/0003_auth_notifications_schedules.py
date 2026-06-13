"""Extend users (auth/terms/onboarding), add notifications + scheduled_scans tables.

All additive: new user columns are nullable or have server defaults so existing
rows are unaffected. scans.user_id and target verification columns already exist
(added in earlier migrations / models) and are intentionally NOT touched here.

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-13 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return insp.has_table(table)


def upgrade() -> None:
    # ── Extend users (only add columns that don't already exist) ──
    user_cols = [
        ("name",                 sa.Column("name", sa.String(255), nullable=True)),
        ("company_name",         sa.Column("company_name", sa.String(255), nullable=True)),
        ("password_hash",        sa.Column("password_hash", sa.String(255), nullable=True)),
        ("api_key",              sa.Column("api_key", sa.String(255), nullable=True)),
        ("terms_accepted",       sa.Column("terms_accepted", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("terms_accepted_at",    sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True)),
        ("terms_version",        sa.Column("terms_version", sa.String(20), nullable=True)),
        ("onboarding_completed", sa.Column("onboarding_completed", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("notify_on_complete",   sa.Column("notify_on_complete", sa.Boolean(), server_default=sa.text("false"), nullable=False)),
        ("notification_email",   sa.Column("notification_email", sa.String(320), nullable=True)),
    ]
    for name, col in user_cols:
        if not _has_column("users", name):
            op.add_column("users", col)
    # index on api_key for lookups
    try:
        op.create_index("ix_users_api_key", "users", ["api_key"])
    except Exception:
        pass

    # ── notifications table ──
    if not _has_table("notifications"):
        op.create_table(
            "notifications",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("type", sa.String(50), server_default="system", nullable=False),
            sa.Column("title", sa.String(255), nullable=False),
            sa.Column("message", sa.Text(), nullable=False),
            sa.Column("scan_id", postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("is_read", sa.Boolean(), server_default=sa.text("false"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
        op.create_index("ix_notifications_created_at", "notifications", ["created_at"])

    # ── scheduled_scans table ──
    if not _has_table("scheduled_scans"):
        op.create_table(
            "scheduled_scans",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("target_ip", sa.String(500), nullable=False),
            sa.Column("target_name", sa.String(255), nullable=True),
            sa.Column("phases", postgresql.JSONB(), nullable=True),
            sa.Column("custom_modules", postgresql.JSONB(), nullable=True),
            sa.Column("schedule_type", sa.String(20), server_default="weekly", nullable=False),
            sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_risk_score", sa.Integer(), nullable=True),
        )
        op.create_index("ix_scheduled_scans_user_id", "scheduled_scans", ["user_id"])
        op.create_index("ix_scheduled_scans_next_run_at", "scheduled_scans", ["next_run_at"])


def downgrade() -> None:
    for tbl in ("scheduled_scans", "notifications"):
        if _has_table(tbl):
            op.drop_table(tbl)
    for col in (
        "notification_email", "notify_on_complete", "onboarding_completed",
        "terms_version", "terms_accepted_at", "terms_accepted",
        "api_key", "password_hash", "company_name", "name",
    ):
        if _has_column("users", col):
            op.drop_column("users", col)
