"""Recurring tasks: `tasks.recurrence` holds the rule; finishing a task spawns the next one."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261129_01"
down_revision = "20261128_01"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("tasks")}


def upgrade() -> None:
    if context.is_offline_mode() or "recurrence" not in _columns():
        op.add_column("tasks", sa.Column("recurrence", sa.JSON(), nullable=True))


def downgrade() -> None:
    if context.is_offline_mode() or "recurrence" in _columns():
        with op.batch_alter_table("tasks") as batch:
            batch.drop_column("recurrence")
