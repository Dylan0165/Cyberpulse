"""Add extended scan fields: scan_mode, target_type, credentials, findings, ai_analysis, tool_outputs.

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-03 12:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # All new columns are nullable or have server_default so existing rows are fine.
    op.add_column("scans", sa.Column("scan_mode", sa.String(20), server_default="blackbox", nullable=False))
    op.add_column("scans", sa.Column("target_type", sa.String(50), server_default="web", nullable=False))
    op.add_column("scans", sa.Column("credentials", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("phases_enabled", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("phases_completed", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("findings", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("ai_analysis", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("tool_outputs", postgresql.JSONB(), nullable=True))
    op.add_column("scans", sa.Column("current_phase_num", sa.Integer(), server_default="0", nullable=False))


def downgrade() -> None:
    op.drop_column("scans", "current_phase_num")
    op.drop_column("scans", "tool_outputs")
    op.drop_column("scans", "ai_analysis")
    op.drop_column("scans", "findings")
    op.drop_column("scans", "phases_completed")
    op.drop_column("scans", "phases_enabled")
    op.drop_column("scans", "credentials")
    op.drop_column("scans", "target_type")
    op.drop_column("scans", "scan_mode")
