"""Replace memory_facts with memories (P4 / MEM-01).

Copies existing facts into memories with new ids, then drops memory_facts.
Creates an FTS5 virtual table on SQLite for keyword search.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import context, op

revision = "20261111_07"
down_revision = "20261111_06"
branch_labels = None
depends_on = None


def upgrade() -> None:
    offline = context.is_offline_mode()
    bind = op.get_bind()
    inspector = None if offline else sa.inspect(bind)

    if offline or not inspector.has_table("memories"):
        op.create_table(
            "memories",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(32), nullable=False, server_default="fact"),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("source_run_id", sa.String(64)),
            sa.Column("last_used_at", sa.DateTime(timezone=True)),
            sa.Column("embedding", sa.JSON()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("deleted_at", sa.DateTime(timezone=True)),
            sa.UniqueConstraint("user_id", "kind", "content", name="uq_memories_user_kind_content"),
        )
        op.create_index("ix_memories_user_id", "memories", ["user_id"])
        op.create_index("ix_memories_kind", "memories", ["kind"])
        op.create_index("ix_memories_last_used_at", "memories", ["last_used_at"])
        op.create_index("ix_memories_deleted_at", "memories", ["deleted_at"])

    if not offline and inspector is not None and inspector.has_table("memory_facts"):
        rows = bind.execute(
            sa.text("SELECT user_id, kind, content, created_at FROM memory_facts")
        ).fetchall()
        for user_id, kind, content, created_at in rows:
            bind.execute(
                sa.text(
                    "INSERT OR IGNORE INTO memories "
                    "(id, user_id, kind, content, created_at) "
                    "VALUES (:id, :user_id, :kind, :content, :created_at)"
                ),
                {
                    "id": uuid.uuid4().hex,
                    "user_id": user_id,
                    "kind": kind or "fact",
                    "content": content,
                    "created_at": created_at,
                },
            )
        op.drop_table("memory_facts")

    if not offline and bind.dialect.name == "sqlite":
        bind.execute(
            sa.text(
                "CREATE VIRTUAL TABLE IF NOT EXISTS memory_fts "
                "USING fts5(memory_id UNINDEXED, content, tokenize='porter')"
            )
        )
        bind.execute(
            sa.text(
                "INSERT INTO memory_fts(memory_id, content) "
                "SELECT id, content FROM memories WHERE deleted_at IS NULL"
            )
        )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TABLE IF EXISTS memory_fts")
    op.drop_table("memories")
    op.create_table(
        "memory_facts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(128), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False, server_default="fact"),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "kind", "content", name="uq_user_kind_content"),
    )
