"""Add google_connections.read_only (P7 / INT-GOO-01)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_03"
down_revision = "20261112_02"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    if offline or (inspector is not None and inspector.has_table("google_connections")):
        cols = (
            set() if offline else {c["name"] for c in inspector.get_columns("google_connections")}
        )
        if offline or "read_only" not in cols:
            op.add_column(
                "google_connections",
                sa.Column("read_only", sa.Integer(), nullable=False, server_default="1"),
            )


def downgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    if offline or (inspector is not None and inspector.has_table("google_connections")):
        cols = (
            set() if offline else {c["name"] for c in inspector.get_columns("google_connections")}
        )
        if offline or "read_only" in cols:
            op.drop_column("google_connections", "read_only")
