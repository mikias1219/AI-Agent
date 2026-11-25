"""Migration 20261127_01 on SQLite: task columns, plan_date backfill, sync tables, up/down/up."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

BACKEND = Path(__file__).resolve().parents[2]
TASK_COLUMNS = {
    "plan_date",
    "target_value",
    "target_unit",
    "actual_value",
    "outcome",
    "outcome_note",
    "calendar_event_id",
    "calendar_synced_at",
}
SYNC_TABLES = {"drive_links", "drive_folders", "sync_settings"}


def cfg() -> Config:
    config = Config(str(BACKEND / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND / "migrations"))
    return config


def columns(db: Path, table: str = "tasks") -> set[str]:
    with sqlite3.connect(db) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def tables(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_up_down_up(tmp_path, monkeypatch) -> None:
    db = tmp_path / "mig.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(cfg(), "head")
    assert columns(db) >= TASK_COLUMNS and tables(db) >= SYNC_TABLES
    command.downgrade(cfg(), "20261126_01")
    assert not (TASK_COLUMNS & columns(db)) and not (SYNC_TABLES & tables(db))
    assert "tasks" in tables(db)  # the rest of the schema is untouched
    command.upgrade(cfg(), "head")
    assert columns(db) >= TASK_COLUMNS and tables(db) >= SYNC_TABLES


def test_backfill_uses_due_date_else_created_date_in_owner_timezone(tmp_path, monkeypatch) -> None:
    db = tmp_path / "backfill.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(cfg(), "20261126_01")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "INSERT INTO owner_profile (owner_id, timezone, language, wizard_completed, "
            "checklist, bio, updated_at) VALUES ('nairobi', 'Africa/Nairobi', 'en', 0, '{}', '', "
            "'2026-01-01')"
        )
        conn.execute(
            "INSERT INTO owner_profile (owner_id, timezone, language, wizard_completed, "
            "checklist, bio, updated_at) VALUES ('ny', 'America/New_York', 'en', 0, '{}', '', "
            "'2026-01-01')"
        )
        rows = [
            # id, owner, due_at (UTC), created_at (UTC)
            ("due-nairobi", "nairobi", "2026-11-25 22:30:00.000000", "2026-11-01 10:00:00.000000"),
            ("due-ny", "ny", "2026-11-26 02:30:00.000000", "2026-11-01 10:00:00.000000"),
            ("created-only", "nairobi", None, "2026-11-10 21:30:00.000000"),
            ("no-profile", "ghost", None, "2026-11-10 21:30:00.000000"),
        ]
        for task_id, owner, due, created in rows:
            conn.execute(
                "INSERT INTO tasks (id, owner_user_id, title, description, status, created_at, "
                "updated_at, priority, due_at, project, tags, source, source_ref) VALUES "
                "(?, ?, 't', '', 'planned', ?, ?, 'none', ?, '', '[]', '', '')",
                (task_id, owner, created, created, due),
            )
    command.upgrade(cfg(), "head")
    with sqlite3.connect(db) as conn:
        found = dict(conn.execute("SELECT id, plan_date FROM tasks"))
        defaults = conn.execute(
            "SELECT target_unit, outcome_note, outcome, calendar_event_id FROM tasks LIMIT 1"
        ).fetchone()
    assert found == {
        "due-nairobi": "2026-11-26",  # 22:30 UTC is already the 26th in Nairobi
        "due-ny": "2026-11-25",  # 02:30 UTC is still the evening of the 25th in New York
        "created-only": "2026-11-11",
        "no-profile": "2026-11-10",  # unknown owner falls back to UTC
    }
    assert defaults == ("", "", None, None)


def test_migration_tolerates_a_database_created_by_init_db(tmp_path, monkeypatch) -> None:
    from personal_agent.infrastructure.persistence.database import create_engine_from_url, init_db

    db = tmp_path / "boot.db"
    init_db(create_engine_from_url(f"sqlite:///{db}"))  # tables already have the new shape
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(cfg(), "head")
    assert columns(db) >= TASK_COLUMNS


@pytest.mark.parametrize("table", sorted(SYNC_TABLES))
def test_sync_tables_have_expected_keys(tmp_path, monkeypatch, table) -> None:
    db = tmp_path / "keys.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(cfg(), "head")
    expected = {
        "drive_links": {
            "owner_user_id",
            "object_type",
            "object_id",
            "drive_file_id",
            "drive_url",
            "content_hash",
            "synced_at",
            "local_deleted_at",
        },
        "drive_folders": {"owner_user_id", "path", "folder_id", "folder_url"},
        "sync_settings": {
            "owner_user_id",
            "service",
            "enabled",
            "include",
            "last_sync_at",
            "last_error",
        },
    }[table]
    assert expected <= columns(db, table)
