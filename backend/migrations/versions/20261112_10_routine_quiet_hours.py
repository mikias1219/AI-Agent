"""Add quiet hours and daily_cap to automations (routines)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_10"
down_revision = "20261112_09"
branch_labels = None
depends_on = None


def _columns() -> set[str]:
    if context.is_offline_mode():
        return set()
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("automations"):
        return set()
    return {c["name"] for c in inspector.get_columns("automations")}


def upgrade() -> None:
    cols = _columns()
    offline = context.is_offline_mode()
    if offline or "quiet_hours_start" not in cols:
        op.add_column(
            "automations",
            sa.Column("quiet_hours_start", sa.String(8), nullable=False, server_default=""),
        )
    if offline or "quiet_hours_end" not in cols:
        op.add_column(
            "automations",
            sa.Column("quiet_hours_end", sa.String(8), nullable=False, server_default=""),
        )
    if offline or "daily_cap" not in cols:
        op.add_column(
            "automations",
            sa.Column("daily_cap", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    cols = _columns()
    with op.batch_alter_table("automations") as batch:
        if context.is_offline_mode() or "daily_cap" in cols:
            batch.drop_column("daily_cap")
        if context.is_offline_mode() or "quiet_hours_end" in cols:
            batch.drop_column("quiet_hours_end")
        if context.is_offline_mode() or "quiet_hours_start" in cols:
            batch.drop_column("quiet_hours_start")
