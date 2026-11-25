"""Google Calendar sync for tasks (contract section 9): offline against an in-memory fake."""

from __future__ import annotations

import json

import pytest

from personal_agent.domain.models import ToolCall, ToolContext
from tests.sync_support import (
    NO_DRIVE_SCOPES,
    OWNER,
    Clock,
    FakeGoogle,
    build_sync_app,
    dashboard_client,
    utc,
)

NOW = utc(2026, 11, 25, 8)


@pytest.fixture()
def env(tmp_path, monkeypatch):
    clock = Clock(NOW)
    container, fake = build_sync_app(tmp_path, clock)
    client = dashboard_client(container, tmp_path, monkeypatch)
    return container, fake, client, clock


def make(client, title="Dentist", **extra):
    resp = client.post("/api/tasks", json={"title": title, **extra})
    assert resp.status_code == 201, resp.text
    return resp.json()


def approve(container, approval_id):
    return container.approval_service.decide(approval_id, True, actor=OWNER, channel="dashboard")


def run(client, container, **body):
    resp = client.post("/api/calendar-sync/run", json=body)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    if data["status"] == "awaiting_approval":
        return approve(container, data["approval_id"])
    return data


def event_body(fake, index=0):
    return list(fake.events.values())[index]


def test_status_shape(env) -> None:
    container, _, client, _ = env
    make(client, due="2026-11-25 15:30")
    status = client.get("/api/calendar-sync/status").json()
    assert status == {
        "connected": True,
        "scope_granted": True,
        "enabled": False,
        "mode": "ask",
        "last_sync_at": None,
        "last_error": None,
        "pending": 1,
    }
    assert (
        client.patch("/api/calendar-sync/settings", json={"enabled": True}).json()["enabled"]
        is True
    )
    assert client.patch("/api/calendar-sync/settings", json={"enabled": "x"}).status_code == 400


def test_only_timed_tasks_are_pushed(env) -> None:
    container, fake, client, _ = env
    timed = make(client, "Dentist", due="2026-11-25 15:30")
    make(client, "Date only", due="2026-11-26")  # resolves to the 09:00 default: date only
    make(client, "No due at all")
    assert client.get("/api/calendar-sync/status").json()["pending"] == 1
    out = run(client, container)
    assert json.loads(out.output)["created"] == 1
    assert len(fake.events) == 1
    event = event_body(fake)
    assert event["summary"] == "Dentist"
    assert event["start"] == {"dateTime": "2026-11-25T15:30:00Z", "timeZone": "UTC"}
    assert event["end"] == {"dateTime": "2026-11-25T16:00:00Z", "timeZone": "UTC"}
    assert "Managed by AURA" in event["description"]
    stored = client.get(f"/api/tasks/{timed['id']}").json()
    assert stored["calendar_event_id"] == "evt1" and stored["calendar_synced_at"]


def test_all_day_option_pushes_date_only_tasks_as_all_day_events(env) -> None:
    container, fake, client, _ = env
    make(client, "Date only", due="2026-11-26")
    assert client.post("/api/calendar-sync/run", json={}).json()["status"] == "nothing_to_do"
    out = run(client, container, all_day=True)
    assert json.loads(out.output)["created"] == 1
    event = event_body(fake)
    assert event["start"] == {"date": "2026-11-26"} and event["end"] == {"date": "2026-11-27"}
    assert client.post("/api/calendar-sync/run", json={"all_day": "yes"}).status_code == 400


def test_ask_mode_is_one_approval_with_titles_and_no_writes_before_it(env) -> None:
    container, fake, client, _ = env
    make(client, "One", due="2026-11-25 10:30")
    make(client, "Two", due="2026-11-25 11:30")
    resp = client.post("/api/calendar-sync/run", json={}).json()
    assert resp["status"] == "awaiting_approval" and resp["summary"] is None
    assert fake.requests == []
    approvals = container.approvals_repository.find(limit=10)
    assert len(approvals) == 1 and approvals[0].tool_name == "task_calendar_sync"
    assert len(approvals[0].arguments["task_ids"]) == 2
    assert sorted(approvals[0].arguments["titles"]) == ["One", "Two"]
    out = approve(container, resp["approval_id"])
    assert out.ok and json.loads(out.output)["created"] == 2
    assert approve(container, resp["approval_id"]).executed is False
    assert len(fake.calls("POST")) == 2


def test_auto_mode_runs_without_an_approval(env) -> None:
    container, fake, client, _ = env
    make(client, due="2026-11-25 15:30")
    container.agent_control.patch(OWNER, tool_permissions={"task_calendar_sync": "allow"})
    assert client.get("/api/calendar-sync/status").json()["mode"] == "auto"
    resp = client.post("/api/calendar-sync/run", json={}).json()
    assert resp == {
        "status": "done",
        "approval_id": None,
        "summary": {"created": 1, "updated": 0, "skipped": 0, "failed": 0},
    }
    assert container.approvals_repository.find(limit=5) == []


@pytest.mark.parametrize(
    ("outcome", "prefix"),
    [("achieved", "✓ "), ("partial", "◐ "), ("missed", "✗ "), ("skipped", "– ")],
)
def test_completion_updates_the_prefix_and_description(env, outcome, prefix) -> None:
    container, fake, client, clock = env
    task = make(client, "Push-ups", due="2026-11-25 15:30", target_value=30, target_unit="push-ups")
    run(client, container)
    assert event_body(fake)["summary"] == "Push-ups"
    clock.advance(hours=1)
    client.post(
        f"/api/tasks/{task['id']}/complete",
        json={"outcome": outcome, "actual_value": 12, "note": "knees hurt"},
    )
    assert client.get("/api/calendar-sync/status").json()["pending"] == 1
    out = run(client, container)
    assert json.loads(out.output)["updated"] == 1
    event = event_body(fake)
    assert event["summary"] == prefix + "Push-ups"
    assert f"Outcome: {outcome}" in event["description"]
    assert "12/30 push-ups" in event["description"] and "knees hurt" in event["description"]
    assert len(fake.events) == 1  # updated, not duplicated
    assert [r.method for r in fake.calls(contains="/events")] == ["POST", "PATCH"]


def test_reopening_removes_the_prefix_again(env) -> None:
    container, fake, client, clock = env
    task = make(client, "Run", due="2026-11-25 15:30")
    run(client, container)
    clock.advance(minutes=1)
    client.post(f"/api/tasks/{task['id']}/complete", json={})
    run(client, container)
    assert event_body(fake)["summary"].startswith("✓ ")
    clock.advance(minutes=1)
    client.post(f"/api/tasks/{task['id']}/reopen")
    run(client, container)
    assert event_body(fake)["summary"] == "Run"
    assert "Outcome" not in event_body(fake)["description"]


def test_synced_tasks_are_left_alone_until_they_change(env) -> None:
    container, fake, client, clock = env
    task = make(client, "Run", due="2026-11-25 15:30")
    run(client, container)
    assert client.post("/api/calendar-sync/run", json={}).json()["status"] == "nothing_to_do"
    clock.advance(minutes=2)
    client.patch(f"/api/tasks/{task['id']}", json={"title": "Run 5k"})
    out = run(client, container)
    assert json.loads(out.output)["updated"] == 1
    assert event_body(fake)["summary"] == "Run 5k"


def test_old_and_cancelled_tasks_are_not_backfilled(env) -> None:
    container, fake, client, _ = env
    make(client, "Ancient", due="2026-11-10 15:30")
    cancelled = make(client, "Dropped", due="2026-11-25 15:30")
    client.patch(f"/api/tasks/{cancelled['id']}", json={"status": "cancelled"})
    assert client.get("/api/calendar-sync/status").json()["pending"] == 0
    assert client.post("/api/calendar-sync/run", json={}).json()["status"] == "nothing_to_do"
    assert fake.requests == []


def test_event_deleted_in_google_is_recreated(env) -> None:
    container, fake, client, clock = env
    task = make(client, "Run", due="2026-11-25 15:30")
    run(client, container)
    fake.events.clear()
    clock.advance(minutes=1)
    client.patch(f"/api/tasks/{task['id']}", json={"title": "Run again"})
    out = json.loads(run(client, container).output)
    assert (out["created"], out["failed"]) == (1, 0)
    assert client.get(f"/api/tasks/{task['id']}").json()["calendar_event_id"] != "evt1"


def test_never_deletes_events(env) -> None:
    container, fake, client, _ = env
    task = make(client, due="2026-11-25 15:30")
    run(client, container)
    client.delete(f"/api/tasks/{task['id']}")
    assert client.get("/api/calendar-sync/status").json()["pending"] == 0
    assert fake.deletes == [] and len(fake.events) == 1


def test_batch_is_capped_at_25_tasks(env) -> None:
    container, fake, client, _ = env
    for index in range(30):
        make(
            client, f"T{index}", due=f"2026-11-25 {10 + index // 4:02d}:{(index % 4) * 15 + 5:02d}"
        )
    assert client.get("/api/calendar-sync/status").json()["pending"] == 30
    resp = client.post("/api/calendar-sync/run", json={}).json()
    arguments = container.approvals_repository.find(limit=3)[0].arguments
    assert len(arguments["task_ids"]) == 25
    assert json.loads(approve(container, resp["approval_id"]).output)["created"] == 25
    assert client.get("/api/calendar-sync/status").json()["pending"] == 5


def test_connection_problems_are_409(tmp_path, monkeypatch) -> None:
    for scopes, message in [
        (None, "Google Calendar is not connected."),
        (
            NO_DRIVE_SCOPES.replace("calendar.events", "calendar.readonly"),
            "Reconnect Google to allow Calendar sync.",
        ),
    ]:
        sub = tmp_path / str(scopes is None)
        sub.mkdir()
        container, fake = build_sync_app(sub, Clock(NOW), scopes=scopes)
        client = dashboard_client(container, sub, monkeypatch)
        make(client, due="2026-11-25 15:30")
        resp = client.post("/api/calendar-sync/run", json={})
        assert resp.status_code == 409 and resp.json() == {"detail": message}
        status = client.get("/api/calendar-sync/status").json()
        assert status["scope_granted"] is False
        assert fake.requests == []


def test_read_only_google_blocks_calendar_writes(tmp_path, monkeypatch) -> None:
    container, fake = build_sync_app(tmp_path, Clock(NOW), read_only=True)
    client = dashboard_client(container, tmp_path, monkeypatch)
    make(client, due="2026-11-25 15:30")
    resp = client.post("/api/calendar-sync/run", json={})
    assert resp.status_code == 409 and "Read-only" in resp.json()["detail"]
    assert fake.requests == []
    # the client itself also refuses, whoever calls it
    from personal_agent.infrastructure.integrations.google.clients import GoogleApiError

    with pytest.raises(GoogleApiError, match="Read-only"):
        FakeGoogle().client(read_only=True).create_calendar_event(
            title="x", starts_at="2026-11-25T10:00:00Z", ends_at="2026-11-25T10:30:00Z"
        )


def test_google_refusal_aborts_and_is_reported(env) -> None:
    container, fake, client, _ = env
    make(client, due="2026-11-25 15:30")
    fake.fail_status["calendar"] = 403
    out = run(client, container)
    assert out.ok is False
    assert "403" in client.get("/api/calendar-sync/status").json()["last_error"]


def test_calendar_tool_runs_only_through_the_gate(env) -> None:
    container, fake, client, _ = env
    task = make(client, due="2026-11-25 15:30")
    spec = next(s for s in container.registry.specs() if s.name == "task_calendar_sync")
    assert spec.access_kind == "execute"
    ctx = ToolContext(user_id=OWNER, session_id="s", origin="cli")
    from personal_agent.domain.exceptions import ApprovalPendingError

    with pytest.raises(ApprovalPendingError):
        container.registry.execute(
            ToolCall(id="c", name="task_calendar_sync", arguments={"task_ids": [task["id"]]}), ctx
        )
    assert fake.requests == []
    with pytest.raises(Exception, match="Bad arguments"):
        container.registry.execute(
            ToolCall(id="c", name="task_calendar_sync", arguments={"task_ids": []}), ctx
        )


def test_foreign_or_missing_task_ids_fail_without_calls(env) -> None:
    container, fake, _, _ = env
    container.agent_control.patch(OWNER, tool_permissions={"task_calendar_sync": "allow"})
    ctx = ToolContext(user_id=OWNER, session_id="s", origin="cli")
    result = container.registry.execute(
        ToolCall(id="c", name="task_calendar_sync", arguments={"task_ids": ["nope"]}), ctx
    )
    out = json.loads(result.output)
    assert out["failed"] == 1 and fake.requests == []
