"""Public demo scans (no auth) for the marketing site.

Revision ID: 0014
Revises: 0013
Create Date: 2026-06-27 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0014"
down_revision: Union[str, None] = "0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def upgrade() -> None:
    if not _has_table("demo_scans"):
        op.create_table(
            "demo_scans",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("ip_address", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), server_default="pending", nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("terminal_output", sa.Text(), nullable=True),
            sa.Column("findings", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("ws_token", sa.String(64), nullable=False, unique=True),
        )


def downgrade() -> None:
    if _has_table("demo_scans"):
        op.drop_table("demo_scans")
