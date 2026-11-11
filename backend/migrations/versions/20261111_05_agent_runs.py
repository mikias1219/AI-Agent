"""Add agent_runs and run_steps (AGT-01, AGT-02, OBS-01).

Plain CREATE TABLE guarded by an inspector so it is safe after `init_db` bootstrapped the
tables; works on SQLite and PostgreSQL.
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261111_05"
down_revision = "20261111_04"
branch_labels = None
depends_on = None


def upgrade():
    offline = context.is_offline_mode()
    inspector = None if offline else sa.inspect(op.get_bind())

    if offline or not inspector.has_table("agent_runs"):
        op.create_table(
            "agent_runs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("session_id", sa.String(64)),
            sa.Column("user_id", sa.String(128)),
            sa.Column("origin", sa.String(32)),
            sa.Column("status", sa.String(24)),
            sa.Column("prompt_version", sa.String(128)),
            sa.Column("model", sa.String(128), nullable=False, server_default=""),
            sa.Column("input_text", sa.Text()),
            sa.Column("final_text", sa.Text()),
            sa.Column("error", sa.Text()),
            sa.Column("stop_reason", sa.String(32)),
            sa.Column("created_at", sa.DateTime(timezone=True)),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
        )
        op.create_index("ix_agent_runs_session_id", "agent_runs", ["session_id"])
        op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
        op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    if offline or not inspector.has_table("run_steps"):
        op.create_table(
            "run_steps",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column(
                "run_id",
                sa.String(64),
                sa.ForeignKey("agent_runs.id", ondelete="CASCADE"),
            ),
            sa.Column("seq", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(16)),
            sa.Column("name", sa.String(128)),
            sa.Column("status", sa.String(16)),
            sa.Column("arguments", sa.JSON()),
            sa.Column("output", sa.Text()),
            sa.Column("error", sa.Text()),
            sa.Column("started_at", sa.DateTime(timezone=True)),
            sa.Column("finished_at", sa.DateTime(timezone=True)),
            sa.Column("duration_ms", sa.Integer()),
        )
        op.create_index("ix_run_steps_run_id", "run_steps", ["run_id"])


def downgrade():
    op.drop_index("ix_run_steps_run_id", table_name="run_steps")
    op.drop_table("run_steps")
    op.drop_index("ix_agent_runs_status", table_name="agent_runs")
    op.drop_index("ix_agent_runs_user_id", table_name="agent_runs")
    op.drop_index("ix_agent_runs_session_id", table_name="agent_runs")
    op.drop_table("agent_runs")
