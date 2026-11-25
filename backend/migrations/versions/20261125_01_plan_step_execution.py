"""Plan step arguments, result and approval id (plan executor)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261125_01"
down_revision = "20261120_01"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns("plan_steps")}


def upgrade() -> None:
    offline = context.is_offline_mode()
    existing = set() if offline else _columns()
    if offline or "arguments" not in existing:
        op.add_column("plan_steps", sa.Column("arguments", sa.JSON(), nullable=True))
    if offline or "result" not in existing:
        op.add_column(
            "plan_steps", sa.Column("result", sa.Text(), nullable=False, server_default="")
        )
    if offline or "approval_id" not in existing:
        op.add_column("plan_steps", sa.Column("approval_id", sa.String(64), nullable=True))


def downgrade() -> None:
    if context.is_offline_mode():
        return
    existing = _columns()
    with op.batch_alter_table("plan_steps") as batch:
        for name in ("approval_id", "result", "arguments"):
            if name in existing:
                batch.drop_column(name)
