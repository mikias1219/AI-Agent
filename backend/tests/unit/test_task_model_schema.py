"""Defaults and persistence of the extended Task / OwnerProfile schema (offline, temp SQLite)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from personal_agent.domain.models import OwnerProfile, Task, TaskPriority, TaskStatus
from personal_agent.infrastructure.persistence.repositories import TaskRepositoryImpl

BACKEND = Path(__file__).resolve().parents[2]


def test_task_defaults() -> None:
    task = Task(id="t1", title="x")
    assert task.priority is TaskPriority.NONE
    assert task.due_at is None
    assert task.project == ""
    assert task.tags == []
    assert task.source == "" and task.source_ref == ""
    assert task.completed_at is None
    assert task.deleted_at is None
    assert task.is_deleted is False
    assert task.description == ""


def test_task_tags_not_shared_between_instances() -> None:
    a, b = Task(id="a", title="a"), Task(id="b", title="b")
    a.tags.append("home")
    assert b.tags == []


def test_owner_profile_defaults() -> None:
    profile = OwnerProfile(owner_id="default")
    assert profile.timezone == "UTC"
    assert profile.language == "en"
    assert profile.name is None


def test_task_round_trips_new_fields(session_factory) -> None:
    repo = TaskRepositoryImpl(session_factory)
    due = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
    repo.add(
        Task(
            id="t1",
            title="Pay rent",
            description="notes",
            priority=TaskPriority.P1,
            due_at=due,
            project="home",
            tags=["money", "monthly"],
            source="chat",
            source_ref="msg-1",
            created_at=due,
            updated_at=due,
        )
    )
    loaded = repo.get("t1")
    assert loaded is not None
    assert loaded.priority is TaskPriority.P1
    assert loaded.project == "home"
    assert loaded.tags == ["money", "monthly"]
    assert (loaded.source, loaded.source_ref) == ("chat", "msg-1")
    assert loaded.due_at is not None and loaded.due_at.replace(tzinfo=UTC) == due

    loaded.status = TaskStatus.DONE
    loaded.completed_at = due
    loaded.deleted_at = due
    repo.save(loaded)
    again = repo.get("t1")
    assert again is not None and again.completed_at is not None and again.is_deleted


def _alembic(db: Path) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


def _upgrade(db: Path, monkeypatch: pytest.MonkeyPatch, revision: str = "head") -> None:
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(_alembic(db), revision)


def _columns(db: Path, table: str) -> set[str]:
    with sqlite3.connect(db) as conn:
        return {row[1] for row in conn.execute(f"PRAGMA table_info({table})")}


def test_migration_on_fresh_database(tmp_path, monkeypatch) -> None:
    db = tmp_path / "fresh.db"
    _upgrade(db, monkeypatch)
    assert {"priority", "due_at", "project", "tags", "deleted_at", "completed_at"} <= _columns(
        db, "tasks"
    )
    assert {"owner_id", "name", "timezone", "language"} <= _columns(db, "owner_profile")


def test_migration_upgrades_legacy_tasks_table(tmp_path, monkeypatch) -> None:
    db = tmp_path / "legacy.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE tasks (id VARCHAR(64) PRIMARY KEY, owner_user_id VARCHAR(128), "
            "title VARCHAR(256) NOT NULL, description TEXT, status VARCHAR(32), "
            "created_at DATETIME, updated_at DATETIME)"
        )
        conn.execute("INSERT INTO tasks (id, title, status) VALUES ('old', 'Old', 'planned')")
    _upgrade(db, monkeypatch)
    assert "deleted_at" in _columns(db, "tasks")
    with sqlite3.connect(db) as conn:
        row = conn.execute("SELECT priority, project, deleted_at FROM tasks").fetchone()
    assert row == ("none", "", None)


def test_approvals_migration_adds_durable_columns_and_expires_legacy_rows(
    tmp_path, monkeypatch
) -> None:
    db = tmp_path / "approvals.db"
    _upgrade(db, monkeypatch, "20261111_05")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE approvals (id VARCHAR(64) PRIMARY KEY, tool_name VARCHAR(128) "
            "NOT NULL, arguments_json TEXT, user_id VARCHAR(128), session_id VARCHAR(64), "
            "origin VARCHAR(32), status VARCHAR(16), created_at DATETIME, decided_at DATETIME)"
        )
        conn.execute("INSERT INTO approvals (id, tool_name, status) VALUES ('old', 't', 'pending')")
    _upgrade(db, monkeypatch)
    assert {"run_id", "arguments_hash", "expires_at", "risk", "untrusted_content"} <= _columns(
        db, "approvals"
    )
    with sqlite3.connect(db) as conn:
        assert conn.execute("SELECT status FROM approvals").fetchone() == ("expired",)


def test_approvals_migration_creates_table_on_fresh_database(tmp_path, monkeypatch) -> None:
    db = tmp_path / "fresh-approvals.db"
    _upgrade(db, monkeypatch)
    assert {"run_id", "call_id", "arguments_hash", "expires_at", "result"} <= _columns(
        db, "approvals"
    )


def test_memories_migration_replaces_facts(tmp_path, monkeypatch) -> None:
    db = tmp_path / "memories.db"
    _upgrade(db, monkeypatch, "20261111_06")
    with sqlite3.connect(db) as conn:
        conn.execute(
            "CREATE TABLE memory_facts (id INTEGER PRIMARY KEY, user_id VARCHAR(128), "
            "kind VARCHAR(32), content TEXT NOT NULL, created_at DATETIME)"
        )
        conn.execute(
            "INSERT INTO memory_facts (user_id, kind, content, created_at) "
            "VALUES ('alice', 'preference', 'Likes tea', '2026-01-01')"
        )
    _upgrade(db, monkeypatch)
    assert {"id", "user_id", "kind", "content", "embedding", "deleted_at"} <= _columns(
        db, "memories"
    )
    with sqlite3.connect(db) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master")}
        assert "memory_facts" not in tables
        row = conn.execute("SELECT user_id, kind, content FROM memories").fetchone()
    assert row == ("alice", "preference", "Likes tea")
