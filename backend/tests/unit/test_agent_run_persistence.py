"""Unit: AgentRun / RunStep persistence, migration, and event plumbing (AGT-01, AGT-02)."""

from __future__ import annotations

import sqlite3
import threading
from datetime import UTC, datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config

from personal_agent.application.run_events import (
    FanoutSink,
    RecordingEventSink,
    RunEventBroker,
    RunStepRecorder,
)
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import AgentRun, RunEvent, RunStatus, RunStep, StepStatus
from personal_agent.infrastructure.persistence.repositories import AgentRunRepositoryImpl

BACKEND = Path(__file__).resolve().parents[2]


@pytest.fixture()
def run_repo(session_factory) -> AgentRunRepositoryImpl:
    return AgentRunRepositoryImpl(session_factory)


def _run(run_id: str = "r1", **overrides) -> AgentRun:
    fields = {
        "id": run_id,
        "session_id": "s1",
        "user_id": "dashboard",
        "origin": "dashboard",
        "prompt_version": "system_v1@2026-11-11/UTC/en",
        "input_text": "hi",
        "created_at": datetime(2026, 11, 11, 12, 0, tzinfo=UTC),
    }
    fields.update(overrides)
    return AgentRun(**fields)


def test_run_round_trip_and_status_update(run_repo) -> None:
    run_repo.create(_run())
    loaded = run_repo.get("r1")
    assert loaded is not None
    assert loaded.status is RunStatus.RUNNING
    assert loaded.prompt_version == "system_v1@2026-11-11/UTC/en"
    assert loaded.created_at == datetime(2026, 11, 11, 12, 0, tzinfo=UTC)

    loaded.status = RunStatus.COMPLETED
    loaded.final_text = "done"
    loaded.finished_at = datetime(2026, 11, 11, 12, 1, tzinfo=UTC)
    run_repo.save(loaded)
    again = run_repo.get("r1")
    assert again is not None
    assert (again.status, again.final_text) == (RunStatus.COMPLETED, "done")
    assert again.created_at == datetime(2026, 11, 11, 12, 0, tzinfo=UTC)
    assert again.finished_at == datetime(2026, 11, 11, 12, 1, tzinfo=UTC)


def test_unknown_run_is_none_and_save_raises(run_repo) -> None:
    assert run_repo.get("nope") is None
    with pytest.raises(StorageError):
        run_repo.save(_run("nope"))


def test_steps_are_ordered_and_updatable(run_repo) -> None:
    run_repo.create(_run())
    run_repo.add_step(RunStep(id="b", run_id="r1", seq=2, kind="tool", name="second"))
    first = RunStep(id="a", run_id="r1", seq=1, kind="tool", name="first", arguments={"x": 1})
    run_repo.add_step(first)
    first.status, first.output, first.duration_ms = StepStatus.OK, "ok", 12
    run_repo.save_step(first)

    steps = run_repo.list_steps("r1")
    assert [s.name for s in steps] == ["first", "second"]
    assert steps[0].arguments == {"x": 1}
    assert (steps[0].status, steps[0].duration_ms) == (StepStatus.OK, 12)


def test_list_recent_filters_by_user(run_repo) -> None:
    run_repo.create(_run("r1"))
    run_repo.create(_run("r2", user_id="other"))
    assert [r.id for r in run_repo.list_recent(user_id="other")] == ["r2"]
    assert {r.id for r in run_repo.list_recent()} == {"r1", "r2"}


def test_recording_sink_keeps_order() -> None:
    sink = RecordingEventSink()
    sink.emit(RunEvent(run_id="r", type="run.started"))
    sink.emit(RunEvent(run_id="r", type="token", data={"text": "a"}))
    assert sink.types == ["run.started", "token"]


def test_fanout_isolates_a_failing_sink() -> None:
    class Broken:
        def emit(self, event: RunEvent) -> None:
            raise RuntimeError("boom")

    good = RecordingEventSink()
    FanoutSink([Broken(), good]).emit(RunEvent(run_id="r", type="token"))
    assert good.types == ["token"]


def test_step_recorder_persists_tool_events(run_repo) -> None:
    run_repo.create(_run())
    recorder = RunStepRecorder(run_repo)
    recorder.emit(
        RunEvent("r1", "tool.started", {"call_id": "c1", "name": "t", "arguments": {"a": 1}})
    )
    assert run_repo.list_steps("r1")[0].status is StepStatus.RUNNING
    recorder.emit(
        RunEvent(
            "r1", "tool.finished", {"call_id": "c1", "ok": False, "output": "bad", "duration_ms": 5}
        )
    )
    step = run_repo.list_steps("r1")[0]
    assert (step.status, step.error, step.duration_ms) == (StepStatus.FAILED, "bad", 5)
    assert step.arguments == {"a": 1}


def test_broker_assigns_seq_and_follows_until_terminal() -> None:
    broker = RunEventBroker()
    broker.open("r")
    received: list[RunEvent] = []

    def listen() -> None:
        received.extend(e for e in broker.follow("r", idle_timeout=0.05) if e is not None)

    thread = threading.Thread(target=listen)
    thread.start()
    broker.emit(RunEvent("r", "run.started"))
    broker.emit(RunEvent("r", "token", {"text": "x"}))
    broker.emit(RunEvent("r", "run.completed"))
    thread.join(timeout=3)

    assert [(e.seq, e.type) for e in received] == [
        (1, "run.started"),
        (2, "token"),
        (3, "run.completed"),
    ]
    assert [e.seq for e in broker.follow("r", after_seq=2) if e] == [3]


def _alembic(db: Path) -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "migrations"))
    return cfg


def _tables(db: Path) -> set[str]:
    with sqlite3.connect(db) as conn:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def test_migration_creates_run_tables_and_downgrades(tmp_path, monkeypatch) -> None:
    db = tmp_path / "m.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db}")
    command.upgrade(_alembic(db), "head")
    assert {"agent_runs", "run_steps"} <= _tables(db)
    command.downgrade(_alembic(db), "20261111_04")
    assert not {"agent_runs", "run_steps"} & _tables(db)
