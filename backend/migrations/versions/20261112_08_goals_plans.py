"""Add goals, plans and plan_steps (spec §9.2)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_08"
down_revision = "20261112_07"
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    offline = context.is_offline_mode()
    if offline or not _has_table("goals"):
        op.create_table(
            "goals",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("success_criteria", sa.JSON()),
            sa.Column("progress", sa.Float(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(16), nullable=False, server_default="active"),
            sa.Column("next_step", sa.Text(), nullable=False, server_default=""),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_goals_owner_user_id", "goals", ["owner_user_id"])
        op.create_index("ix_goals_status", "goals", ["status"])
    if offline or not _has_table("plans"):
        op.create_table(
            "plans",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("goal_id", sa.String(64)),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("title", sa.String(256), nullable=False, server_default=""),
            sa.Column("status", sa.String(16), nullable=False, server_default="proposed"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_plans_goal_id", "plans", ["goal_id"])
        op.create_index("ix_plans_owner_user_id", "plans", ["owner_user_id"])
        op.create_index("ix_plans_status", "plans", ["status"])
    if offline or not _has_table("plan_steps"):
        op.create_table(
            "plan_steps",
            sa.Column(
                "plan_id",
                sa.String(64),
                sa.ForeignKey("plans.id", ondelete="CASCADE"),
                primary_key=True,
            ),
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("tool_name", sa.String(128)),
            sa.Column("access_kind", sa.String(16), nullable=False, server_default="prepare"),
            sa.Column("status", sa.String(16), nullable=False, server_default="planned"),
            sa.Column("depends_on", sa.JSON()),
        )
        op.create_index("ix_plan_steps_plan_id", "plan_steps", ["plan_id"])


def downgrade() -> None:
    offline = context.is_offline_mode()
    for table in ("plan_steps", "plans", "goals"):
        if offline or _has_table(table):
            op.drop_table(table)
