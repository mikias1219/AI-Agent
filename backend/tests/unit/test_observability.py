"""Unit tests for tracing helpers and extended health (OBS-02, OBS-05)."""

from __future__ import annotations

from personal_agent.application.tracing import new_trace_id
from personal_agent.domain.models import RunEvent
from personal_agent.infrastructure.observability.health import build_health_payload
from personal_agent.infrastructure.observability.run_tracing import TracingEventSink
from personal_agent.infrastructure.observability.tracing import (
    ConsoleExporter,
    NoopExporter,
    Tracer,
    build_tracer,
)


def test_trace_id_is_32_hex():
    tid = new_trace_id()
    assert len(tid) == 32
    int(tid, 16)


def test_build_tracer_none_and_console():
    assert isinstance(build_tracer("none").exporter, NoopExporter)
    assert isinstance(build_tracer("console").exporter, ConsoleExporter)


def test_tracing_event_sink_closes_run_span():
    tracer = Tracer(NoopExporter())
    sink = TracingEventSink(tracer)
    sink.emit(
        RunEvent(
            run_id="r1",
            type="run.started",
            data={"trace_id": "abc", "model": "fake", "origin": "cli"},
        )
    )
    sink.emit(
        RunEvent(
            run_id="r1",
            type="tool.started",
            data={"call_id": "c1", "name": "task_list", "arguments": {}},
        )
    )
    sink.emit(
        RunEvent(
            run_id="r1",
            type="tool.finished",
            data={"call_id": "c1", "name": "task_list", "ok": True, "duration_ms": 3},
        )
    )
    sink.emit(RunEvent(run_id="r1", type="run.completed", data={"stop_reason": None}))
    assert sink._runs == {}  # noqa: SLF001


def test_health_payload_degraded_on_db_failure():
    def boom() -> None:
        raise RuntimeError("db down")

    payload = build_health_payload(
        base={"environment": "local"},
        database_ping=boom,
        audit_list=lambda **_: [],
        provider="fake",
        ollama_reachable=False,
        openai_key_present=False,
        telegram_worker_running=False,
    )
    assert payload["status"] == "degraded"
    assert payload["database"]["ok"] is False
    assert payload["provider_probe"]["ok"] is True
