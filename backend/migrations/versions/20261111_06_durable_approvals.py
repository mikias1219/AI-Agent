"""Extend approvals for durable pause/resume (APR-01..06).

Adds run link, arguments hash, risk, summary, untrusted flag, expiry, decider, channel and
result columns. Pending rows from before this migration have no hash or expiry and could
never be executed safely, so they are marked expired. Works on SQLite and PostgreSQL
(plain ADD COLUMN guarded by an inspector, safe after `init_db` created the new schema).
"""

import sqlalchemy as sa
from alembic import context, op

revision = "20261111_06"
down_revision = "20261111_05"
branch_labels = None
depends_on = None


def _new_columns() -> list[tuple[str, sa.Column]]:
    return [
        ("run_id", sa.Column("run_id", sa.String(64))),
        ("call_id", sa.Column("call_id", sa.String(64), nullable=False, server_default="")),
        (
            "arguments_hash",
            sa.Column("arguments_hash", sa.String(64), nullable=False, server_default=""),
        ),
        ("risk", sa.Column("risk", sa.String(16), nullable=False, server_default="medium")),
        ("summary", sa.Column("summary", sa.Text())),
        (
            "untrusted_content",
            sa.Column("untrusted_content", sa.Integer(), nullable=False, server_default="0"),
        ),
        ("expires_at", sa.Column("expires_at", sa.DateTime(timezone=True))),
        ("decided_by", sa.Column("decided_by", sa.String(128), nullable=False, server_default="")),
        ("channel", sa.Column("channel", sa.String(32), nullable=False, server_default="")),
        ("result", sa.Column("result", sa.Text())),
        ("edited_from", sa.Column("edited_from", sa.String(64))),
    ]


def _create_table() -> None:
    """Fresh databases never had an approvals table (it came from `init_db`)."""
    op.create_table(
        "approvals",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("tool_name", sa.String(128), nullable=False),
        sa.Column("arguments_json", sa.Text()),
        sa.Column("user_id", sa.String(128)),
        sa.Column("session_id", sa.String(64)),
        sa.Column("origin", sa.String(32)),
        sa.Column("status", sa.String(16)),
        sa.Column("created_at", sa.DateTime(timezone=True)),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        *[column for _, column in _new_columns()],
    )
    op.create_index("ix_approvals_user_id", "approvals", ["user_id"])
    op.create_index("ix_approvals_status", "approvals", ["status"])
    op.create_index("ix_approvals_run_id", "approvals", ["run_id"])
    op.create_index("ix_approvals_expires_at", "approvals", ["expires_at"])


def upgrade():
    offline = context.is_offline_mode()
    existing: set[str] = set()
    indexes: set[str] = set()
    if not offline:
        inspector = sa.inspect(op.get_bind())
        if not inspector.has_table("approvals"):
            _create_table()
            return
        existing = {c["name"] for c in inspector.get_columns("approvals")}
        indexes = {i["name"] for i in inspector.get_indexes("approvals")}
    for name, column in _new_columns():
        if offline or name not in existing:
            op.add_column("approvals", column)
    if offline or "ix_approvals_run_id" not in indexes:
        op.create_index("ix_approvals_run_id", "approvals", ["run_id"])
    if offline or "ix_approvals_expires_at" not in indexes:
        op.create_index("ix_approvals_expires_at", "approvals", ["expires_at"])
    op.execute(
        "UPDATE approvals SET status = 'expired' WHERE status = 'pending' AND expires_at IS NULL"
    )


def downgrade():
    op.drop_index("ix_approvals_expires_at", table_name="approvals")
    op.drop_index("ix_approvals_run_id", table_name="approvals")
    with op.batch_alter_table("approvals") as batch:
        for name, _ in reversed(_new_columns()):
            batch.drop_column(name)
