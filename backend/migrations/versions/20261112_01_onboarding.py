"""Add first-run wizard and checklist fields to owner_profile (P5 / UX-02)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_01"
down_revision = "20261111_07"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)
    cols = set() if offline else {c["name"] for c in inspector.get_columns("owner_profile")}

    if offline or "wizard_completed" not in cols:
        op.add_column(
            "owner_profile",
            sa.Column("wizard_completed", sa.Integer(), nullable=False, server_default="0"),
        )
    if offline or "checklist" not in cols:
        op.add_column(
            "owner_profile",
            sa.Column("checklist", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    op.drop_column("owner_profile", "checklist")
    op.drop_column("owner_profile", "wizard_completed")
