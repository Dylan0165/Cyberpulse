"""2FA (TOTP) + API keys + team members.

ADDITIVE + idempotent. users gets totp_* columns; new api_keys and team_members
tables. No changes to existing columns.

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-26 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0013"
down_revision: Union[str, None] = "0012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


_USER_COLUMNS = [
    ("totp_secret", sa.Column("totp_secret", sa.String(255), nullable=True)),
    ("totp_enabled", sa.Column("totp_enabled", sa.Boolean(), server_default=sa.false(), nullable=False)),
    ("totp_backup_codes", sa.Column("totp_backup_codes", postgresql.JSONB(), nullable=True)),
]


def upgrade() -> None:
    for name, col in _USER_COLUMNS:
        if not _has_column("users", name):
            op.add_column("users", col)

    if not _has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("key_hash", sa.String(128), nullable=False, unique=True),
            sa.Column("key_prefix", sa.String(32), nullable=False),
            sa.Column("scopes", postgresql.JSONB(), server_default=sa.text("'[\"scan:read\",\"scan:create\"]'::jsonb"), nullable=False),
            sa.Column("last_used", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_api_keys_user_id", "api_keys", ["user_id"])
        op.create_index("ix_api_keys_key_hash", "api_keys", ["key_hash"])

    if not _has_table("team_members"):
        op.create_table(
            "team_members",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("member_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True),
            sa.Column("email", sa.String(320), nullable=False),
            sa.Column("role", sa.String(20), server_default="viewer", nullable=False),
            sa.Column("invited_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_team_members_owner_id", "team_members", ["owner_id"])
        op.create_unique_constraint("uq_team_owner_email", "team_members", ["owner_id", "email"])


def downgrade() -> None:
    if _has_table("team_members"):
        op.drop_table("team_members")
    if _has_table("api_keys"):
        op.drop_table("api_keys")
    for name, _ in reversed(_USER_COLUMNS):
        if _has_column("users", name):
            op.drop_column("users", name)
