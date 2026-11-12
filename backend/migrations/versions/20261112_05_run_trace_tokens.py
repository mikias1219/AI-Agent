"""Add trace_id and token columns on agent_runs (OBS-01, OBS-02)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_05"
down_revision = "20261112_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    columns = {c["name"] for c in (inspector.get_columns("agent_runs") if inspector else [])}
    if offline or "trace_id" not in columns:
        op.add_column(
            "agent_runs",
            sa.Column("trace_id", sa.String(64), nullable=False, server_default=""),
        )
    if offline or "input_tokens" not in columns:
        op.add_column("agent_runs", sa.Column("input_tokens", sa.Integer(), nullable=True))
    if offline or "output_tokens" not in columns:
        op.add_column("agent_runs", sa.Column("output_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "output_tokens")
    op.drop_column("agent_runs", "input_tokens")
    op.drop_column("agent_runs", "trace_id")
