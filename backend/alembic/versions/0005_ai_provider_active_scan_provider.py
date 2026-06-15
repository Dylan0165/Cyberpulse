"""Add ai_provider_active to users; ai_provider_used + custom_config to scans.

Additive + idempotent (skips columns that already exist).

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-15 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("users", "ai_provider_active"):
        op.add_column("users", sa.Column(
            "ai_provider_active", sa.Boolean(), server_default=sa.text("false"), nullable=False))
    if not _has_column("scans", "ai_provider_used"):
        op.add_column("scans", sa.Column("ai_provider_used", sa.String(30), nullable=True))
    if not _has_column("scans", "custom_config"):
        op.add_column("scans", sa.Column("custom_config", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    for tbl, col in (("scans", "custom_config"), ("scans", "ai_provider_used"),
                     ("users", "ai_provider_active")):
        if _has_column(tbl, col):
            op.drop_column(tbl, col)
