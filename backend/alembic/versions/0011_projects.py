"""Scan projects — bundle multiple scans under one project + combined report.

Adds `scan_projects` and a nullable `scans.project_id`. Idempotent.

Revision ID: 0011
Revises: 0010
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0011"
down_revision: Union[str, None] = "0010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def upgrade() -> None:
    if not _has_table("scan_projects"):
        op.create_table(
            "scan_projects",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("description", sa.String(1000), nullable=True),
            sa.Column("status", sa.String(32), server_default="active", nullable=False),
            sa.Column("total_scans", sa.Integer(), server_default="0", nullable=False),
            sa.Column("completed_scans", sa.Integer(), server_default="0", nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_scan_projects_user_id", "scan_projects", ["user_id"])

    if not _has_column("scans", "project_id"):
        op.add_column(
            "scans",
            sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=True),
        )
        try:
            op.create_foreign_key(
                "fk_scans_project_id", "scans", "scan_projects",
                ["project_id"], ["id"], ondelete="SET NULL",
            )
        except Exception:
            pass


def downgrade() -> None:
    if _has_column("scans", "project_id"):
        try:
            op.drop_constraint("fk_scans_project_id", "scans", type_="foreignkey")
        except Exception:
            pass
        op.drop_column("scans", "project_id")
    if _has_table("scan_projects"):
        op.drop_table("scan_projects")
