"""Pending memory proposals for Memory Proposed tab (MEM-02)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261113_01"
down_revision = "20261112_10"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    offline = context.is_offline_mode()
    if offline or not _has_table("memory_proposals"):
        op.create_table(
            "memory_proposals",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False, server_default="fact"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_run_id", sa.String(64)),
            sa.Column("source", sa.Text(), nullable=False, server_default=""),
            sa.Column("status", sa.String(16), nullable=False, server_default="proposed"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_memory_proposals_user_id", "memory_proposals", ["user_id"])
        op.create_index("ix_memory_proposals_kind", "memory_proposals", ["kind"])
        op.create_index("ix_memory_proposals_status", "memory_proposals", ["status"])


def downgrade() -> None:
    if context.is_offline_mode() or _has_table("memory_proposals"):
        op.drop_table("memory_proposals")
