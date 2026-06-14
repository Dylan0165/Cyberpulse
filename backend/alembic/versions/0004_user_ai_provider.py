"""Add per-user AI analysis provider preference to users.

Additive only: new columns are nullable or have a server default, so existing
rows are unaffected. Idempotent — skips columns that already exist.

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-14 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    cols = [
        ("ai_provider", sa.Column("ai_provider", sa.String(20), server_default="deepseek", nullable=False)),
        ("ai_api_key",  sa.Column("ai_api_key", sa.String(255), nullable=True)),
        ("ai_base_url", sa.Column("ai_base_url", sa.String(255), nullable=True)),
    ]
    for name, col in cols:
        if not _has_column("users", name):
            op.add_column("users", col)


def downgrade() -> None:
    for col in ("ai_base_url", "ai_api_key", "ai_provider"):
        if _has_column("users", col):
            op.drop_column("users", col)
