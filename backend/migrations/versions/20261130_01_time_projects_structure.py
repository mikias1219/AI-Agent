"""Time entries, projects, task structure (subtasks, blocked-by) and learning-path goals."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20261130_01"
down_revision = "20261129_01"
branch_labels = None
depends_on = None

_TABLES = ("projects", "time_entries")


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def upgrade() -> None:
    from personal_agent.infrastructure.persistence.models import Base

    bind = op.get_bind()
    for name in _TABLES:
        Base.metadata.tables[name].create(bind, checkfirst=True)

    task_cols = _columns("tasks")
    with op.batch_alter_table("tasks") as batch:
        if "parent_id" not in task_cols:
            batch.add_column(sa.Column("parent_id", sa.String(64), nullable=True))
            batch.create_foreign_key(
                "fk_tasks_parent_id", "tasks", ["parent_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_tasks_parent_id", ["parent_id"])
        if "blocked_by" not in task_cols:
            batch.add_column(sa.Column("blocked_by", sa.JSON(), nullable=True))

    goal_cols = _columns("goals")
    with op.batch_alter_table("goals") as batch:
        if "kind" not in goal_cols:
            batch.add_column(
                sa.Column("kind", sa.String(16), nullable=False, server_default="goal")
            )
        if "target_hours" not in goal_cols:
            batch.add_column(sa.Column("target_hours", sa.Float(), nullable=True))
        if "milestones" not in goal_cols:
            batch.add_column(sa.Column("milestones", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("goals") as batch:
        for name in ("milestones", "target_hours", "kind"):
            batch.drop_column(name)
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_parent_id")
        batch.drop_constraint("fk_tasks_parent_id", type_="foreignkey")
        batch.drop_column("blocked_by")
        batch.drop_column("parent_id")
    bind = op.get_bind()
    from personal_agent.infrastructure.persistence.models import Base

    for name in reversed(_TABLES):
        Base.metadata.tables[name].drop(bind, checkfirst=True)
