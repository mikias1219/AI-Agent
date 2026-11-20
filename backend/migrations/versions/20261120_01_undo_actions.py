"""Undo window records for Balanced auto-runs (AG-TRU-04)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261120_01"
down_revision = "20261113_01"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    offline = context.is_offline_mode()
    if offline or not _has_table("undo_actions"):
        op.create_table(
            "undo_actions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("tool_name", sa.String(128), nullable=False),
            sa.Column("summary", sa.Text(), nullable=False, server_default=""),
            sa.Column("entity_id", sa.String(128), nullable=False, server_default=""),
            sa.Column("payload_json", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="open"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("undone_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_undo_actions_owner_user_id", "undo_actions", ["owner_user_id"])
        op.create_index("ix_undo_actions_status", "undo_actions", ["status"])
        op.create_index("ix_undo_actions_expires_at", "undo_actions", ["expires_at"])


def downgrade() -> None:
    if context.is_offline_mode() or _has_table("undo_actions"):
        op.drop_table("undo_actions")
