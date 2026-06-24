"""Multi-target scanning: CIDR / IP-range / subdomain discovery.

ADDITIVE + idempotent. Adds discovery/grouping columns to `targets` and a
`multi_scan_jobs` table that tracks a fan-out of per-host scans. `target_type`
already exists on `targets` (single/domain/ip/...), so it is NOT re-added.

Revision ID: 0009
Revises: 0008
Create Date: 2026-06-24 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0009"
down_revision: Union[str, None] = "0008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_column(table: str, column: str) -> bool:
    insp = sa.inspect(op.get_bind())
    return any(c["name"] == column for c in insp.get_columns(table))


def _has_table(table: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(table)


_TARGET_COLUMNS = [
    ("cidr_notation", sa.Column("cidr_notation", sa.String(64), nullable=True)),
    ("ip_range_start", sa.Column("ip_range_start", sa.String(64), nullable=True)),
    ("ip_range_end", sa.Column("ip_range_end", sa.String(64), nullable=True)),
    ("discovered_hosts", sa.Column("discovered_hosts", postgresql.JSONB(), nullable=True)),
    ("parent_target_id", sa.Column("parent_target_id", postgresql.UUID(as_uuid=True), nullable=True)),
]


def upgrade() -> None:
    for name, col in _TARGET_COLUMNS:
        if not _has_column("targets", name):
            op.add_column("targets", col)

    # Self-referential FK for child hosts within a CIDR/range parent target.
    if _has_column("targets", "parent_target_id"):
        try:
            op.create_foreign_key(
                "fk_targets_parent_target_id",
                "targets",
                "targets",
                ["parent_target_id"],
                ["id"],
                ondelete="CASCADE",
            )
        except Exception:
            # FK may already exist (idempotent re-run) — ignore.
            pass

    if not _has_table("multi_scan_jobs"):
        op.create_table(
            "multi_scan_jobs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
            sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("job_type", sa.String(32), nullable=False),  # cidr | range | subdomain
            sa.Column("input", sa.String(500), nullable=False),
            sa.Column("status", sa.String(32), nullable=False, server_default="discovering"),
            sa.Column("total_hosts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("scanned_hosts", sa.Integer(), server_default="0", nullable=False),
            sa.Column("credits_used", sa.Integer(), server_default="0", nullable=False),
            sa.Column("scan_ids", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb"), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_multi_scan_jobs_user_id", "multi_scan_jobs", ["user_id"])


def downgrade() -> None:
    if _has_table("multi_scan_jobs"):
        op.drop_table("multi_scan_jobs")

    if _has_column("targets", "parent_target_id"):
        try:
            op.drop_constraint("fk_targets_parent_target_id", "targets", type_="foreignkey")
        except Exception:
            pass
    for name, _ in reversed(_TARGET_COLUMNS):
        if _has_column("targets", name):
            op.drop_column("targets", name)
