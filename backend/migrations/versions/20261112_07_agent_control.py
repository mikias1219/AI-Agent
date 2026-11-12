"""Add agent_control_json to owner_profile (autonomy preset, pause, daily counters)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_07"
down_revision = "20261112_06"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    if context.is_offline_mode():
        return set()
    inspector = sa.inspect(op.get_bind())
    return {c["name"] for c in inspector.get_columns("owner_profile")}


def upgrade() -> None:
    if context.is_offline_mode() or "agent_control_json" not in _columns():
        op.add_column("owner_profile", sa.Column("agent_control_json", sa.Text(), nullable=True))


def downgrade() -> None:
    if context.is_offline_mode() or "agent_control_json" in _columns():
        with op.batch_alter_table("owner_profile") as batch:  # SQLite-safe drop
            batch.drop_column("agent_control_json")
