"""/api/runs lifecycle, event stream, cancel, and /api/chat compatibility."""

from __future__ import annotations

import base64
import hashlib
import json
import threading

from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.domain.models import AssistantTurn, ToolCall
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app
from tests.conftest import make_spy_tool

PASSWORD = "correct horse battery staple"
SALT = b"runs-api-test-salt"


def _build(tmp_path, provider):
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'runs-api.db'}",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    container = build_app(settings=settings, provider=provider)
    client = TestClient(
        create_dashboard_app(container=container, frontend_dir=frontend),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client, container


def _events(client: TestClient, run_id: str, **params) -> list[dict]:
    response = client.get(f"/api/runs/{run_id}/events", params=params)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/x-ndjson")
    return [json.loads(line) for line in response.text.splitlines() if line.strip()]


def test_run_lifecycle_events_and_steps(tmp_path):
    provider = FakeProvider(
        [
            AssistantTurn(tool_calls=(ToolCall(id="c1", name="report_time", arguments={}),)),
            AssistantTurn(content="It is 12:00."),
        ]
    )
    client, container = _build(tmp_path, provider)
    container.registry.register(make_spy_tool("report_time", output="12:00"))

    started = client.post("/api/runs", json={"text": "what time is it?"})
    assert started.status_code == 202
    run = started.json()
    assert run["prompt_version"].startswith("system_v1@") and run["session_id"]

    events = _events(client, run["id"])
    assert [e["type"] for e in events] == [
        "run.started",
        "tool.started",
        "tool.finished",
        "token",
        "run.completed",
    ]
    assert [e["seq"] for e in events] == [1, 2, 3, 4, 5]
    assert events[-1]["data"]["reply"] == "It is 12:00."

    # Resuming from a sequence number returns only the tail.
    assert [e["seq"] for e in _events(client, run["id"], after=3)] == [4, 5]

    detail = client.get(f"/api/runs/{run['id']}").json()
    assert detail["status"] == "completed" and detail["reply"] == "It is 12:00."
    assert [(s["name"], s["status"]) for s in detail["steps"]] == [("report_time", "ok")]
    assert [r["id"] for r in client.get("/api/runs").json()] == [run["id"]]


def test_finished_run_is_replayed_from_storage(tmp_path):
    client, container = _build(tmp_path, FakeProvider(["hello"]))
    run = client.post("/api/runs", json={"text": "hi"}).json()
    _events(client, run["id"])  # wait until finished

    container.runs._broker._buffers.clear()  # simulate a restart: nothing in memory
    events = _events(client, run["id"])

    assert [e["type"] for e in events] == ["run.started", "run.completed"]
    assert events[-1]["data"]["reply"] == "hello"


def test_cancel_stops_the_run_between_steps(tmp_path):
    client, container = _build(tmp_path, FakeProvider())
    gate, release = threading.Event(), threading.Event()
    ran: list[str] = []

    from personal_agent.domain.models import ToolSpec

    def blocking(_ctx, _args) -> str:
        ran.append("blocking")
        gate.set()
        release.wait(5)
        return "first done"

    container.registry.register(
        ToolSpec("blocking", "b", {"type": "object", "properties": {}}, "read", blocking)
    )
    container.registry.register(make_spy_tool("never"))
    container.agent._provider._script = [
        AssistantTurn(
            tool_calls=(
                ToolCall(id="c1", name="blocking", arguments={}),
                ToolCall(id="c2", name="never", arguments={}),
            )
        )
    ]

    run = client.post("/api/runs", json={"text": "go"}).json()
    assert gate.wait(5)
    cancelled = client.post(f"/api/runs/{run['id']}/cancel")
    assert cancelled.status_code == 202
    release.set()

    events = _events(client, run["id"])
    assert [e["type"] for e in events] == [
        "run.started",
        "tool.started",
        "tool.finished",
        "run.failed",
    ]
    assert events[-1]["data"]["status"] == "cancelled"
    detail = client.get(f"/api/runs/{run['id']}").json()
    assert detail["status"] == "cancelled" and len(detail["steps"]) == 1
    assert ran == ["blocking"]

    # Cancelling again is harmless.
    assert client.post(f"/api/runs/{run['id']}/cancel").json()["status"] == "cancelled"


def test_unknown_run_and_blank_text_are_rejected(tmp_path):
    client, _ = _build(tmp_path, FakeProvider())
    assert client.get("/api/runs/nope").status_code == 404
    assert client.get("/api/runs/nope/events").status_code == 404
    assert client.post("/api/runs/nope/cancel").status_code == 404
    assert client.post("/api/runs", json={"text": ""}).status_code == 422
    assert client.post("/api/runs", json={"text": "   "}).status_code == 400


def test_runs_require_login(tmp_path):
    client, _ = _build(tmp_path, FakeProvider())
    client.post("/api/logout")
    assert client.post("/api/runs", json={"text": "hi"}).status_code == 401
    assert client.get("/api/runs").status_code == 401


def test_chat_endpoint_still_works_and_records_a_run(tmp_path):
    client, _ = _build(tmp_path, FakeProvider(["Hi there."]))

    reply = client.post("/api/chat", json={"text": "hello"})

    assert reply.status_code == 200 and reply.json()["reply"] == "Hi there."
    (run,) = client.get("/api/runs").json()
    assert run["status"] == "completed" and run["reply"] == "Hi there."
    assert run["session_id"] == reply.json()["session_id"]


def test_chat_stream_still_streams_and_records_a_run(tmp_path):
    client, _ = _build(tmp_path, FakeProvider(["Streamed."]))

    response = client.post("/api/chat/stream", json={"text": "hello"})

    types = [json.loads(line)["type"] for line in response.text.splitlines() if line]
    assert types == ["delta", "done"]
    assert len(client.get("/api/runs").json()) == 1
