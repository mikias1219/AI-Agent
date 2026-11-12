"""Add result_type and result_json to run_steps (R4)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261112_06"
down_revision = "20261112_05"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("run_steps")}
    if "result_type" not in columns:
        op.add_column(
            "run_steps",
            sa.Column(
                "result_type",
                sa.String(length=64),
                server_default="generic",
                nullable=False,
            ),
        )
    if "result_json" not in columns:
        op.add_column("run_steps", sa.Column("result_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    columns = {c["name"] for c in inspector.get_columns("run_steps")}
    if "result_json" in columns:
        op.drop_column("run_steps", "result_json")
    if "result_type" in columns:
        op.drop_column("run_steps", "result_type")
