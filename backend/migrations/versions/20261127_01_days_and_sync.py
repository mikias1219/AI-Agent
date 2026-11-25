"""Tasks as achievements and days, Drive links and sync settings (contract sections 7-9)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from zoneinfo import ZoneInfo

import sqlalchemy as sa
from alembic import context, op

revision = "20261127_01"
down_revision = "20261126_01"
branch_labels = None
depends_on = None

_TASK_COLUMNS = (
    ("plan_date", lambda: sa.Column("plan_date", sa.Date(), nullable=True)),
    ("target_value", lambda: sa.Column("target_value", sa.Float(), nullable=True)),
    (
        "target_unit",
        lambda: sa.Column("target_unit", sa.String(20), nullable=False, server_default=""),
    ),
    ("actual_value", lambda: sa.Column("actual_value", sa.Float(), nullable=True)),
    ("outcome", lambda: sa.Column("outcome", sa.String(16), nullable=True)),
    (
        "outcome_note",
        lambda: sa.Column("outcome_note", sa.String(500), nullable=False, server_default=""),
    ),
    (
        "calendar_event_id",
        lambda: sa.Column("calendar_event_id", sa.String(128), nullable=True),
    ),
    (
        "calendar_synced_at",
        lambda: sa.Column("calendar_synced_at", sa.DateTime(timezone=True), nullable=True),
    ),
)
_TABLES = ("drive_links", "drive_folders", "sync_settings")


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def _columns(table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}


def _as_utc(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    if not isinstance(value, datetime):
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _backfill_plan_dates() -> None:
    """plan_date = date of due_at, else created date, in the owner's timezone."""
    bind = op.get_bind()
    zones: dict[str, ZoneInfo] = {}
    if sa.inspect(bind).has_table("owner_profile"):
        for owner, name in bind.execute(sa.text("SELECT owner_id, timezone FROM owner_profile")):
            try:
                zones[str(owner)] = ZoneInfo(str(name or "UTC"))
            except Exception:  # noqa: BLE001 - unknown zone name: fall back to UTC
                zones[str(owner)] = ZoneInfo("UTC")
    rows = bind.execute(
        sa.text("SELECT id, owner_user_id, due_at, created_at FROM tasks WHERE plan_date IS NULL")
    ).fetchall()
    utc = ZoneInfo("UTC")
    tasks = sa.table("tasks", sa.column("id", sa.String), sa.column("plan_date", sa.Date))
    for task_id, owner, due_at, created_at in rows:
        moment = _as_utc(due_at) or _as_utc(created_at) or datetime.now(UTC)
        local: date = moment.astimezone(zones.get(str(owner), utc)).date()
        bind.execute(tasks.update().where(tasks.c.id == task_id).values(plan_date=local))


def upgrade() -> None:
    offline = context.is_offline_mode()
    existing = set() if offline else _columns("tasks")
    for name, make in _TASK_COLUMNS:
        if offline or name not in existing:
            op.add_column("tasks", make())
    if not offline:
        _backfill_plan_dates()
        indexes = {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("tasks")}
        if "ix_tasks_plan_date" not in indexes:
            op.create_index("ix_tasks_plan_date", "tasks", ["plan_date"])
    else:
        op.create_index("ix_tasks_plan_date", "tasks", ["plan_date"])

    if offline or not _has_table("drive_links"):
        op.create_table(
            "drive_links",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_user_id", sa.String(128), nullable=False),
            sa.Column("object_type", sa.String(16), nullable=False),
            sa.Column("object_id", sa.String(64), nullable=False),
            sa.Column("drive_file_id", sa.String(200), nullable=False),
            sa.Column("drive_url", sa.String(500), nullable=False, server_default=""),
            sa.Column("content_hash", sa.String(64), nullable=False, server_default=""),
            sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("local_deleted_at", sa.DateTime(timezone=True), nullable=True),
            sa.UniqueConstraint(
                "owner_user_id", "object_type", "object_id", name="uq_drive_links_object"
            ),
        )
        op.create_index("ix_drive_links_owner_user_id", "drive_links", ["owner_user_id"])
    if offline or not _has_table("drive_folders"):
        op.create_table(
            "drive_folders",
            sa.Column("owner_user_id", sa.String(128), primary_key=True),
            sa.Column("path", sa.String(400), primary_key=True),
            sa.Column("folder_id", sa.String(200), nullable=False),
            sa.Column("folder_url", sa.String(500), nullable=False, server_default=""),
        )
    if offline or not _has_table("sync_settings"):
        op.create_table(
            "sync_settings",
            sa.Column("owner_user_id", sa.String(128), primary_key=True),
            sa.Column("service", sa.String(16), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("include", sa.JSON(), nullable=False),
            sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_error", sa.String(500), nullable=False, server_default=""),
        )


def downgrade() -> None:
    if context.is_offline_mode():
        return
    for table in reversed(_TABLES):
        if _has_table(table):
            op.drop_table(table)
    existing = _columns("tasks")
    with op.batch_alter_table("tasks") as batch:
        if "ix_tasks_plan_date" in {
            i["name"] for i in sa.inspect(op.get_bind()).get_indexes("tasks")
        }:
            batch.drop_index("ix_tasks_plan_date")
        for name, _make in reversed(_TASK_COLUMNS):
            if name in existing:
                batch.drop_column(name)
