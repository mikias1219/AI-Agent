"""Today aggregate, agenda honesty, active run, and the control/today HTTP surface."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.application.services.today_service import (
    CALENDAR_UNAVAILABLE,
    CalendarAgendaService,
)
from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import ApprovalPendingError
from personal_agent.domain.models import (
    AgentRun,
    RunStatus,
    TaskPriority,
    ToolCall,
    ToolContext,
)
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app
from tests.conftest import make_spy_tool

OWNER = "dashboard"
PASSWORD = "correct horse battery staple"
SALT = b"today-test-salt"
REQUIRED_KEYS = {
    "greeting",
    "needs_you",
    "now_next",
    "plan",
    "goals",
    "since_last_looked",
    "onboarding",
    "connections",
    "briefing",
}


def _build(tmp_path):
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'today.db'}",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    container = build_app(settings=settings, provider=FakeProvider())
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    client = TestClient(
        create_dashboard_app(container=container, frontend_dir=frontend),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client, container


@pytest.fixture()
def app(tmp_path):
    return _build(tmp_path)


def test_today_build_has_required_keys(app) -> None:
    _, container = app
    payload = container.today.build(OWNER)
    assert set(payload) >= REQUIRED_KEYS
    assert payload["goals"] == []
    assert payload["since_last_looked"] == []
    assert payload["plan"]["plan_id"] is None


def test_today_without_google_has_no_invented_events(app) -> None:
    _, container = app
    payload = container.today.build(OWNER)
    assert payload["now_next"]["events"] == []
    assert payload["now_next"]["calendar_connected"] is False
    assert payload["now_next"]["active_run"] is None
    warnings = payload["connections"]["warnings"]
    assert [w["id"] for w in warnings] == ["google"]
    assert warnings[0]["action"]["href"] == "/connections"
    # No briefing has been generated: nothing is claimed about the day.
    assert payload["greeting"]["summary"] is None
    assert payload["briefing"]["sections"] == []


def test_needs_you_lists_at_most_three_pending_approvals(app) -> None:
    _, container = app
    container.registry.register(make_spy_tool("send_thing", "execute"))
    ctx = ToolContext(user_id=OWNER, session_id="s", origin="dashboard")
    for i in range(5):
        with pytest.raises(ApprovalPendingError):
            container.registry.execute(ToolCall(id=f"c{i}", name="send_thing", arguments={}), ctx)

    needs_you = container.today.build(OWNER)["needs_you"]
    assert len(needs_you) == 3
    assert {item["kind"] for item in needs_you} == {"approval"}
    assert all(item["tool_name"] == "send_thing" for item in needs_you)


def test_plan_lists_only_open_tasks_due_today(app) -> None:
    _, container = app
    noon = datetime.now(UTC).replace(hour=12, minute=0, second=0, microsecond=0)
    container.tasks.create(
        "Due now-ish", owner_user_id=OWNER, priority=TaskPriority.P1, due_at=noon
    )
    container.tasks.create("Next week", owner_user_id=OWNER, due_at=noon + timedelta(days=7))
    container.tasks.create("No date", owner_user_id=OWNER)

    titles = [t["title"] for t in container.today.build(OWNER)["plan"]["tasks"]]
    assert titles == ["Due now-ish"]


def test_agenda_disconnected_is_honest_empty(app) -> None:
    client, _ = app
    body = client.get("/api/calendar/agenda?limit=3").json()
    assert body == {"connected": False, "events": []}


def test_agenda_connected_returns_provider_events_limited() -> None:
    events = [{"id": str(i), "title": f"E{i}", "startsAt": "", "location": ""} for i in range(5)]
    service = CalendarAgendaService(connected=lambda: True, fetch=lambda limit: events)
    body = service.get(3)
    assert body["connected"] is True
    assert [e["id"] for e in body["events"]] == ["0", "1", "2"]


def test_agenda_provider_failure_is_an_error_not_fake_events() -> None:
    def boom(_limit: int):
        raise RuntimeError("quota")

    body = CalendarAgendaService(connected=lambda: True, fetch=boom).get(3)
    assert body == {"connected": True, "events": [], "error": CALENDAR_UNAVAILABLE}


def test_active_run_endpoint_returns_null_then_live_run(app) -> None:
    client, container = app
    assert client.get("/api/runs/active").json() is None

    done = AgentRun(
        id="r-done", session_id="s", user_id=OWNER, origin="dashboard", prompt_version="v"
    )
    done.status = RunStatus.COMPLETED
    live = AgentRun(
        id="r-live", session_id="s", user_id=OWNER, origin="dashboard", prompt_version="v"
    )
    live.status = RunStatus.AWAITING_APPROVAL
    other = AgentRun(id="r-other", session_id="s", user_id="x", origin="cli", prompt_version="v")
    for run in (done, live, other):
        container.runs_repository.create(run)

    active = client.get("/api/runs/active").json()
    assert active["id"] == "r-live"
    assert active["status"] == "awaiting_approval"
    assert container.today.build(OWNER)["now_next"]["active_run"]["id"] == "r-live"


def test_control_endpoints_round_trip(app) -> None:
    client, container = app
    assert client.get("/api/agent/control").json()["autonomy_preset"] == "ask_first"

    patched = client.patch(
        "/api/agent/control", json={"paused": True, "autonomy_preset": "balanced"}
    )
    assert patched.status_code == 200
    assert patched.json()["paused"] is True
    assert patched.json()["autonomy_preset"] == "balanced"
    assert container.agent_control.is_paused(OWNER) is True

    assert client.patch("/api/agent/control", json={"autonomy_preset": "nope"}).status_code == 422


def test_pause_through_api_blocks_registry_execute(app) -> None:
    client, container = app
    container.registry.register(make_spy_tool("draft_thing", "prepare"))
    ctx = ToolContext(user_id=OWNER, session_id="s", origin="dashboard")
    call = ToolCall(id="c", name="draft_thing", arguments={})

    client.patch("/api/agent/control", json={"paused": True})
    from personal_agent.domain.exceptions import PermissionDeniedError

    with pytest.raises(PermissionDeniedError):
        container.registry.execute(call, ctx)
    client.patch("/api/agent/control", json={"paused": False})
    assert container.registry.execute(call, ctx).ok


def test_today_endpoint_returns_aggregate(app) -> None:
    client, _ = app
    response = client.get("/api/today")
    assert response.status_code == 200
    assert set(response.json()) >= REQUIRED_KEYS
