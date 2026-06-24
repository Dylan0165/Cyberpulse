"""Scanix Agents — local network scanning via an outbound-only agent.

Adds the `scanix_agents` table. Idempotent create.

Revision ID: 0010
Revises: 0009
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0010"
down_revision: Union[str, None] = "0009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("scanix_agents"):
        op.create_table(
            "scanix_agents",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("agent_token", sa.String(255), nullable=False, unique=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("status", sa.String(32), server_default="offline", nullable=False),  # online | offline | scanning
            sa.Column("os", sa.String(32), nullable=True),
            sa.Column("hostname", sa.String(255), nullable=True),
            sa.Column("local_ip", sa.String(64), nullable=True),
            sa.Column("version", sa.String(32), nullable=True),
            sa.Column("last_seen", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        )
        op.create_index("ix_scanix_agents_user_id", "scanix_agents", ["user_id"])
        op.create_index("ix_scanix_agents_agent_token", "scanix_agents", ["agent_token"])


def downgrade() -> None:
    if _has_table("scanix_agents"):
        op.drop_table("scanix_agents")
