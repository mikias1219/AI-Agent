"""Life modules: notes, files, learning, reading, profile photo and profile extras."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import context, op

revision = "20261126_01"
down_revision = "20261125_01"
branch_labels = None
depends_on = None

_TABLES = (
    "notes",
    "files",
    "profile_photos",
    "learn_items",
    "learn_reviews",
    "reading_plans",
    "reading_logs",
)


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _stamp(name: str = "created_at") -> sa.Column:
    return sa.Column(name, sa.DateTime(timezone=True), nullable=False)


def upgrade() -> None:
    offline = context.is_offline_mode()

    if offline or not _has_table("notes"):
        op.create_table(
            "notes",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(8), nullable=False),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("body", sa.Text(), nullable=False, server_default=""),
            sa.Column("tags", sa.JSON(), nullable=False),
            sa.Column("mood", sa.String(8)),
            sa.Column("entry_date", sa.Date()),
            sa.Column("pinned", sa.Boolean(), nullable=False, server_default=sa.false()),
            _stamp(),
            _stamp("updated_at"),
            sa.UniqueConstraint(
                "owner_user_id", "kind", "entry_date", name="uq_notes_owner_kind_date"
            ),
        )
        op.create_index("ix_notes_owner_user_id", "notes", ["owner_user_id"])
        op.create_index("ix_notes_kind", "notes", ["kind"])

    if offline or not _has_table("files"):
        op.create_table(
            "files",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column("mime", sa.String(100), nullable=False),
            sa.Column("size", sa.Integer(), nullable=False),
            sa.Column("kind", sa.String(8), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("tags", sa.JSON(), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            _stamp(),
        )
        op.create_index("ix_files_owner_user_id", "files", ["owner_user_id"])
        op.create_index("ix_files_kind", "files", ["kind"])

    if offline or not _has_table("profile_photos"):
        op.create_table(
            "profile_photos",
            sa.Column("owner_user_id", sa.String(128), primary_key=True),
            sa.Column("mime", sa.String(32), nullable=False),
            sa.Column("content", sa.LargeBinary(), nullable=False),
            sa.Column("etag", sa.String(64), nullable=False),
            _stamp("updated_at"),
        )

    if offline or not _has_table("learn_items"):
        op.create_table(
            "learn_items",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("kind", sa.String(8), nullable=False),
            sa.Column("term", sa.String(200), nullable=False),
            sa.Column("term_key", sa.String(200), nullable=False),
            sa.Column("meaning", sa.String(1000), nullable=False),
            sa.Column("example", sa.String(1000), nullable=False, server_default=""),
            sa.Column("language", sa.String(16), nullable=False, server_default="en"),
            sa.Column("topic", sa.String(60), nullable=False, server_default=""),
            sa.Column("box", sa.Integer(), nullable=False, server_default="0"),
            _stamp("next_review_at"),
            sa.Column("times_correct", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("times_wrong", sa.Integer(), nullable=False, server_default="0"),
            _stamp(),
            _stamp("updated_at"),
            sa.UniqueConstraint(
                "owner_user_id", "language", "term_key", name="uq_learn_owner_term"
            ),
        )
        op.create_index("ix_learn_items_owner_user_id", "learn_items", ["owner_user_id"])
        op.create_index("ix_learn_items_next_review_at", "learn_items", ["next_review_at"])

    if offline or not _has_table("learn_reviews"):
        op.create_table(
            "learn_reviews",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("item_id", sa.String(64), nullable=False),
            sa.Column("result", sa.String(8), nullable=False),
            _stamp("reviewed_at"),
        )
        op.create_index("ix_learn_reviews_owner_user_id", "learn_reviews", ["owner_user_id"])

    if offline or not _has_table("reading_plans"):
        op.create_table(
            "reading_plans",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("items", sa.JSON(), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
            _stamp(),
            _stamp("updated_at"),
        )
        op.create_index("ix_reading_plans_owner_user_id", "reading_plans", ["owner_user_id"])

    if offline or not _has_table("reading_logs"):
        op.create_table(
            "reading_logs",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("reference", sa.String(120), nullable=False),
            sa.Column("read_on", sa.Date(), nullable=False),
            sa.Column("reflection", sa.Text(), nullable=False, server_default=""),
            sa.Column("plan_id", sa.String(64)),
            _stamp(),
        )
        op.create_index("ix_reading_logs_owner_user_id", "reading_logs", ["owner_user_id"])
        op.create_index("ix_reading_logs_read_on", "reading_logs", ["read_on"])
        op.create_index("ix_reading_logs_plan_id", "reading_logs", ["plan_id"])

    existing = set() if offline else _columns("owner_profile")
    if offline or "bio" not in existing:
        op.add_column(
            "owner_profile", sa.Column("bio", sa.String(500), nullable=False, server_default="")
        )
    if offline or "birthday" not in existing:
        op.add_column("owner_profile", sa.Column("birthday", sa.String(10), nullable=True))
    if offline or "notification_prefs" not in existing:
        op.add_column("owner_profile", sa.Column("notification_prefs", sa.JSON(), nullable=True))
    if offline or "created_at" not in existing:
        op.add_column(
            "owner_profile", sa.Column("created_at", sa.DateTime(timezone=True), nullable=True)
        )
        if not offline:
            op.execute("UPDATE owner_profile SET created_at = updated_at WHERE created_at IS NULL")


def downgrade() -> None:
    if context.is_offline_mode():
        return
    for table in reversed(_TABLES):
        if _has_table(table):
            op.drop_table(table)
    existing = _columns("owner_profile")
    with op.batch_alter_table("owner_profile") as batch:
        for name in ("created_at", "notification_prefs", "birthday", "bio"):
            if name in existing:
                batch.drop_column(name)
