"""Add suggestions (spec §9.3): proposals with a mandatory source citation."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_09"
down_revision = "20261112_08"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    offline = context.is_offline_mode()
    if offline or not _has_table("suggestions"):
        op.create_table(
            "suggestions",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False, server_default="idea"),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("reason", sa.Text(), nullable=False, server_default=""),
            sa.Column("source", sa.String(256), nullable=False),
            sa.Column("status", sa.String(16), nullable=False, server_default="new"),
            sa.Column("proposed_action", sa.JSON()),
            sa.Column("expires_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("decided_at", sa.DateTime(timezone=True)),
            sa.Column("feedback", sa.Text(), nullable=False, server_default=""),
            sa.Column("outcome", sa.String(24), nullable=False, server_default=""),
            sa.Column("approval_id", sa.String(64)),
        )
        op.create_index("ix_suggestions_owner_user_id", "suggestions", ["owner_user_id"])
        op.create_index("ix_suggestions_status", "suggestions", ["status"])


def downgrade() -> None:
    if context.is_offline_mode() or _has_table("suggestions"):
        op.drop_table("suggestions")
