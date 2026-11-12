"""Add jobs, reminders and automations (P6 / AUT-01, TSK-05)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261112_02"
down_revision = "20261112_01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)

    if offline or not inspector.has_table("jobs"):
        op.create_table(
            "jobs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("run_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("kind", sa.String(64), nullable=False),
            sa.Column("payload", sa.JSON()),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("last_error", sa.Text()),
            sa.Column("idempotency_key", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("idempotency_key", name="uq_jobs_idempotency_key"),
        )
        op.create_index("ix_jobs_run_at", "jobs", ["run_at"])
        op.create_index("ix_jobs_status", "jobs", ["status"])

    if offline or not inspector.has_table("reminders"):
        op.create_table(
            "reminders",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("remind_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("task_id", sa.String(64)),
            sa.Column("channels", sa.JSON()),
            sa.Column("status", sa.String(16), nullable=False, server_default="pending"),
            sa.Column("late", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("delivered_at", sa.DateTime(timezone=True)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_reminders_remind_at", "reminders", ["remind_at"])
        op.create_index("ix_reminders_status", "reminders", ["status"])

    if offline or not inspector.has_table("automations"):
        op.create_table(
            "automations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(64), nullable=False),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("schedule_time", sa.String(8), nullable=False, server_default="08:00"),
            sa.Column("channels", sa.JSON()),
            sa.Column("last_run_at", sa.DateTime(timezone=True)),
            sa.Column("last_result", sa.Text()),
            sa.Column("last_run_id", sa.String(64)),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint("owner_user_id", "kind", name="uq_automations_owner_kind"),
        )


def downgrade() -> None:
    op.drop_table("automations")
    op.drop_table("reminders")
    op.drop_table("jobs")
