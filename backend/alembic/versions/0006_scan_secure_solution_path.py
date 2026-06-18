"""Add secure_solution_path to scans (pre-generated Secure Solution PDF).

Additive + idempotent (skips the column if it already exists).

Revision ID: 0006
Revises: 0005
Create Date: 2026-06-18 00:00:00.000000
"""

from typing import Sequence, Union
import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_column("scans", "secure_solution_path"):
        op.add_column("scans", sa.Column("secure_solution_path", sa.String(), nullable=True))


def downgrade() -> None:
    if _has_column("scans", "secure_solution_path"):
        op.drop_column("scans", "secure_solution_path")
