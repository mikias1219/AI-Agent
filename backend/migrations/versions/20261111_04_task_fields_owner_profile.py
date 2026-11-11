"""Extend tasks (priority, due date, project, tags, soft delete) and add owner_profile.

The `tasks` table was historically created by `init_db`, not by a migration, so this
revision creates it when missing and otherwise adds only the absent columns. Works on
SQLite and PostgreSQL (plain ADD COLUMN, no ALTER of existing constraints).
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261111_04"
down_revision = "20261111_03"
branch_labels = None
depends_on = None

_NEW_TASK_COLUMNS = (
    lambda: sa.Column("priority", sa.String(8), nullable=False, server_default="none"),
    lambda: sa.Column("due_at", sa.DateTime(timezone=True)),
    lambda: sa.Column("project", sa.String(128), nullable=False, server_default=""),
    lambda: sa.Column("tags", sa.JSON()),
    lambda: sa.Column("source", sa.String(64), nullable=False, server_default=""),
    lambda: sa.Column("source_ref", sa.String(256), nullable=False, server_default=""),
    lambda: sa.Column("completed_at", sa.DateTime(timezone=True)),
    lambda: sa.Column("deleted_at", sa.DateTime(timezone=True)),
)


def _create_tasks() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_user_id", sa.String(128)),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("status", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True)),
        *(make() for make in _NEW_TASK_COLUMNS),
    )
    op.create_index("ix_tasks_owner_user_id", "tasks", ["owner_user_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_due_at", "tasks", ["due_at"])
    op.create_index("ix_tasks_deleted_at", "tasks", ["deleted_at"])


def upgrade():
    offline = context.is_offline_mode()
    inspector = None if offline else sa.inspect(op.get_bind())

    if offline or not inspector.has_table("tasks"):
        _create_tasks()
    else:
        existing = {c["name"] for c in inspector.get_columns("tasks")}
        indexes = {i["name"] for i in inspector.get_indexes("tasks")}
        for make in _NEW_TASK_COLUMNS:
            column = make()
            if column.name not in existing:
                op.add_column("tasks", column)
        for name, col in (("ix_tasks_due_at", "due_at"), ("ix_tasks_deleted_at", "deleted_at")):
            if name not in indexes:
                op.create_index(name, "tasks", [col])

    if offline or not inspector.has_table("owner_profile"):
        op.create_table(
            "owner_profile",
            sa.Column("owner_id", sa.String(128), primary_key=True),
            sa.Column("name", sa.String(80)),
            sa.Column("timezone", sa.String(64), nullable=False, server_default="UTC"),
            sa.Column("language", sa.String(16), nullable=False, server_default="en"),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
        )


def downgrade():
    op.drop_table("owner_profile")
    op.drop_index("ix_tasks_deleted_at", table_name="tasks")
    op.drop_index("ix_tasks_due_at", table_name="tasks")
    with op.batch_alter_table("tasks") as batch:
        for name in (
            "deleted_at",
            "completed_at",
            "source_ref",
            "source",
            "tags",
            "project",
            "due_at",
            "priority",
        ):
            batch.drop_column(name)
