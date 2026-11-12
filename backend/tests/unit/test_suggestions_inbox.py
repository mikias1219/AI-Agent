"""Suggestions and the unified urgency inbox: domain rules, service, HTTP API, Today."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.application.services.suggestion_service import (
    ActionOutcome,
    SuggestionActionFailedError,
    SuggestionService,
)
from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.models import ToolSpec
from personal_agent.domain.suggestions import (
    Suggestion,
    SuggestionError,
    accept_suggestion,
    dismiss_suggestion,
    expire_if_due,
    urgency_score,
    urgency_sort_key,
)
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.suggestion_store import SuggestionRepositoryImpl
from personal_agent.presentation.web.app import create_dashboard_app

OWNER = "dashboard"
PASSWORD = "correct horse battery staple"
SALT = b"suggestions-test-salt"
NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)


def _suggestion(**overrides) -> Suggestion:
    base = {
        "id": "s1",
        "owner_user_id": "o",
        "kind": "idea",
        "title": "Book the dentist",
        "reason": "No visit on record",
        "source": "tasks: dentist (overdue)",
        "status": "new",
    }
    return Suggestion(**{**base, **overrides})


# -- domain ----------------------------------------------------------------------


def test_domain_accept_and_dismiss_only_from_new() -> None:
    accepted = _suggestion()
    accept_suggestion(accepted, now=NOW, outcome="done")
    assert (accepted.status, accepted.outcome, accepted.decided_at) == ("accepted", "done", NOW)
    with pytest.raises(SuggestionError):
        dismiss_suggestion(accepted, now=NOW)
    with pytest.raises(SuggestionError):
        accept_suggestion(accepted, now=NOW, outcome="done")

    dismissed = _suggestion()
    dismiss_suggestion(dismissed, now=NOW, feedback="  not now ")
    assert (dismissed.status, dismissed.feedback) == ("dismissed", "not now")
    with pytest.raises(SuggestionError):
        accept_suggestion(dismissed, now=NOW, outcome="done")


def test_domain_expiry_only_moves_open_suggestions() -> None:
    lapsed = _suggestion(expires_at=NOW - timedelta(minutes=1))
    assert expire_if_due(lapsed, NOW) is True and lapsed.status == "expired"
    assert expire_if_due(lapsed, NOW) is False
    future = _suggestion(expires_at=NOW + timedelta(hours=1))
    assert expire_if_due(future, NOW) is False and future.status == "new"
    kept = _suggestion(status="accepted", expires_at=NOW - timedelta(days=1))
    assert expire_if_due(kept, NOW) is False and kept.status == "accepted"


def test_urgency_orders_approvals_above_suggestions_and_bumps_expiry() -> None:
    high = urgency_score("approval", risk="high", expires_at=None, now=NOW)
    low = urgency_score("approval", risk="low", expires_at=None, now=NOW)
    calm = urgency_score("suggestion", expires_at=None, now=NOW)
    assert high > low > calm
    soon = urgency_score("suggestion", expires_at=NOW + timedelta(hours=1), now=NOW)
    far = urgency_score("suggestion", expires_at=NOW + timedelta(days=3), now=NOW)
    assert soon > far == calm
    assert soon < low  # a nearly-expired idea never outranks a pending approval
    older, newer = NOW - timedelta(hours=2), NOW - timedelta(hours=1)
    assert urgency_sort_key(50, newer) < urgency_sort_key(50, older)
    assert urgency_sort_key(60, older) < urgency_sort_key(50, newer)


# -- service ---------------------------------------------------------------------


class _Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


def _service(session_factory, *, execute=None, clock=None, kinds=None) -> SuggestionService:
    return SuggestionService(
        SuggestionRepositoryImpl(session_factory),
        execute_action=execute,
        access_kind_of=(kinds or {"read_thing": "read", "send_thing": "execute"}).get,
        clock=clock or _Clock(),
    )


def _create(service: SuggestionService, **overrides):
    args = {
        "kind": "followup",
        "title": "Reply to Sam",
        "reason": "Sam wrote 3 days ago",
        "source": "gmail: thread 'Quote' from Sam",
    }
    return service.create(OWNER, **{**args, **overrides})


def test_every_suggestion_needs_a_source_citation(session_factory) -> None:
    service = _service(session_factory)
    for blank in ("", "   "):
        with pytest.raises(SuggestionError, match="Source citation"):
            _create(service, source=blank)
    with pytest.raises(SuggestionError, match="Title"):
        _create(service, title=" ")
    with pytest.raises(SuggestionError, match="unknown tool"):
        _create(service, proposed_action={"tool_name": "nope"})
    with pytest.raises(SuggestionError, match="Unknown proposed_action"):
        _create(service, proposed_action={"tool_name": "read_thing", "shell": "rm"})
    assert service.list(OWNER) == []


def test_persisted_round_trip_and_owner_scoping(session_factory) -> None:
    service = _service(session_factory)
    created = _create(
        service,
        proposed_action={"tool_name": "read_thing", "arguments": {"q": "x"}},
        expires_in=timedelta(days=1),
    )
    loaded = service.get(created.id, OWNER)
    assert loaded.source == "gmail: thread 'Quote' from Sam"
    assert loaded.proposed_action == {"tool_name": "read_thing", "arguments": {"q": "x"}}
    assert loaded.expires_at == NOW + timedelta(days=1)
    assert loaded.created_at == NOW and loaded.status == "new"
    with pytest.raises(StorageError):
        service.get(created.id, "someone-else")
    assert service.list("someone-else") == []


def test_accept_without_action_is_acknowledged_not_executed(session_factory) -> None:
    calls: list[str] = []
    service = _service(
        session_factory, execute=lambda *a: calls.append(a[1]) or ActionOutcome("done")
    )
    item = _create(service)
    result = service.accept(item.id, OWNER)
    assert result.outcome == "acknowledged" and calls == []
    assert service.get(item.id, OWNER).status == "accepted"
    with pytest.raises(SuggestionError):
        service.accept(item.id, OWNER)


def test_accept_runs_action_through_executor_and_records_outcome(session_factory) -> None:
    seen: list[tuple[str, str, dict]] = []

    def execute(owner: str, tool: str, args: dict) -> ActionOutcome:
        seen.append((owner, tool, args))
        return ActionOutcome("pending_approval", "needs ok", approval_id="appr-1")

    service = _service(session_factory, execute=execute)
    item = _create(service, proposed_action={"tool_name": "send_thing", "arguments": {"to": "a"}})
    result = service.accept(item.id, OWNER)
    assert seen == [(OWNER, "send_thing", {"to": "a"})]
    assert result.outcome == "pending_approval"
    stored = service.get(item.id, OWNER)
    assert (stored.status, stored.outcome, stored.approval_id) == (
        "accepted",
        "pending_approval",
        "appr-1",
    )


def test_failed_action_leaves_suggestion_open(session_factory) -> None:
    service = _service(
        session_factory, execute=lambda *_a: ActionOutcome("failed", "Calendar unavailable")
    )
    item = _create(service, proposed_action={"tool_name": "read_thing"})
    with pytest.raises(SuggestionActionFailedError, match="Calendar unavailable"):
        service.accept(item.id, OWNER)
    assert service.get(item.id, OWNER).status == "new"
    no_executor = _service(session_factory)
    with pytest.raises(SuggestionActionFailedError):
        no_executor.accept(item.id, OWNER)


def test_dismiss_keeps_feedback_and_expiry_is_applied_on_read(session_factory) -> None:
    clock = _Clock()
    service = _service(session_factory, clock=clock)
    dismissed = _create(service)
    service.dismiss(dismissed.id, OWNER, "already did this")
    assert service.get(dismissed.id, OWNER).feedback == "already did this"
    short = _create(service, title="Short lived", expires_in=timedelta(hours=1))
    assert [s.id for s in service.open(OWNER)] == [short.id]
    clock.now = NOW + timedelta(hours=2)
    assert service.open(OWNER) == []
    assert service.get(short.id, OWNER).status == "expired"
    with pytest.raises(SuggestionError):
        service.accept(short.id, OWNER)
    assert {s.status for s in service.done(OWNER)} == {"dismissed", "expired"}


# -- HTTP + Today + inbox ----------------------------------------------------------


def _container(tmp_path):
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'inbox.db'}",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    return build_app(settings=settings, provider=FakeProvider())


@pytest.fixture()
def api(tmp_path):
    container = _container(tmp_path)
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>')
    client = TestClient(
        create_dashboard_app(container=container, frontend_dir=frontend),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client, container


def _tool(name: str, kind: str, ran: list[dict]) -> ToolSpec:
    def handler(_ctx, args) -> str:
        ran.append(dict(args))
        return f"ran {name}"

    return ToolSpec(
        name=name,
        description=f"test tool {name}",
        parameters_schema={"type": "object", "properties": {"to": {"type": "string"}}},
        access_kind=kind,  # type: ignore[arg-type]
        handler=handler,
    )


def _pending_approval(container, name: str = "send_thing"):
    from personal_agent.domain.exceptions import ApprovalPendingError
    from personal_agent.domain.models import ToolCall, ToolContext

    ctx = ToolContext(user_id=OWNER, session_id="s", origin="dashboard")
    with pytest.raises(ApprovalPendingError) as pending:
        container.registry.execute(ToolCall(id="c1", name=name, arguments={"to": "x"}), ctx)
    return pending.value.approval_id


def test_inbox_empty_states_and_validation(api) -> None:
    client, _ = api
    body = client.get("/api/inbox").json()
    assert body["items"] == [] and body["counts"] == {"open": 0}
    assert client.get("/api/inbox?tab=done").json()["items"] == []
    assert client.get("/api/inbox?tab=bogus").status_code == 422
    assert client.get("/api/suggestions").json() == []
    assert client.get("/api/suggestions?status=bogus").status_code == 400
    assert client.post("/api/suggestions/nope/accept").status_code == 404
    assert client.post("/api/suggestions/nope/dismiss").status_code == 404


def test_inbox_merges_approvals_and_suggestions_by_urgency(api) -> None:
    client, container = api
    container.registry.register(_tool("send_thing", "execute", []))
    approval_id = _pending_approval(container)
    calm = container.suggestions.create(
        OWNER, kind="idea", title="Calm idea", reason="r", source="tasks: list"
    )
    soon = container.suggestions.create(
        OWNER,
        kind="idea",
        title="Soon idea",
        reason="r",
        source="calendar: Friday",
        expires_in=timedelta(hours=1),
    )
    body = client.get("/api/inbox").json()
    assert body["counts"] == {"open": 3}
    assert [(i["kind"], i["id"]) for i in body["items"]] == [
        ("approval", approval_id),
        ("suggestion", soon.id),
        ("suggestion", calm.id),
    ]
    urgencies = [i["urgency"] for i in body["items"]]
    assert urgencies == sorted(urgencies, reverse=True)
    approval_item, suggestion_item = body["items"][0], body["items"][1]
    assert approval_item["approval"]["actionable"] is True
    assert suggestion_item["source"] == "calendar: Friday"
    assert suggestion_item["suggestion"]["actionable"] is True


def test_suggestion_dismiss_and_accept_move_to_done(api) -> None:
    client, container = api
    first = container.suggestions.create(
        OWNER, kind="idea", title="First", reason="r", source="tasks: x"
    )
    second = container.suggestions.create(
        OWNER, kind="idea", title="Second", reason="r", source="tasks: y"
    )
    dismissed = client.post(f"/api/suggestions/{first.id}/dismiss", json={"feedback": "nope"})
    assert dismissed.status_code == 200
    assert dismissed.json()["suggestion"]["status"] == "dismissed"
    assert client.post(f"/api/suggestions/{first.id}/dismiss").status_code == 409

    accepted = client.post(f"/api/suggestions/{second.id}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["outcome"] == "acknowledged"
    assert client.post(f"/api/suggestions/{second.id}/accept").status_code == 409

    assert client.get("/api/inbox").json() == {"tab": "open", "items": [], "counts": {"open": 0}}
    done = client.get("/api/inbox?tab=done").json()
    assert {i["id"] for i in done["items"]} == {first.id, second.id}
    assert all(i["actionable"] is False for i in done["items"])
    assert [s["id"] for s in client.get("/api/suggestions?status=dismissed").json()] == [first.id]


def test_accepting_execute_action_goes_through_the_approval_gate(api) -> None:
    client, container = api
    ran: list[dict] = []
    container.registry.register(_tool("send_thing", "execute", ran))
    container.registry.register(_tool("read_thing", "read", ran))
    risky = container.suggestions.create(
        OWNER,
        kind="followup",
        title="Send the quote",
        reason="Sam is waiting",
        source="gmail: thread 'Quote'",
        proposed_action={"tool_name": "send_thing", "arguments": {"to": "sam@example.com"}},
    )
    body = client.post(f"/api/suggestions/{risky.id}/accept").json()
    assert body["outcome"] == "pending_approval" and body["approval_id"]
    assert ran == []  # nothing executed without the owner's approval
    pending = {a["id"] for a in client.get("/api/approvals").json()}
    assert body["approval_id"] in pending
    inbox = client.get("/api/inbox").json()
    assert [i["id"] for i in inbox["items"]] == [body["approval_id"]]

    safe = container.suggestions.create(
        OWNER,
        kind="lookup",
        title="Look it up",
        reason="r",
        source="tasks: x",
        proposed_action={"tool_name": "read_thing", "arguments": {}},
    )
    done = client.post(f"/api/suggestions/{safe.id}/accept").json()
    assert done["outcome"] == "done" and ran == [{}]


def test_accept_failure_is_reported_and_suggestion_stays_open(api) -> None:
    client, container = api

    def handler(_ctx, _args) -> str:
        raise RuntimeError("boom")

    container.registry.register(
        ToolSpec(
            name="flaky_thing",
            description="always fails",
            parameters_schema={"type": "object", "properties": {}},
            access_kind="read",
            handler=handler,
        )
    )
    item = container.suggestions.create(
        OWNER,
        kind="lookup",
        title="Flaky",
        reason="r",
        source="tasks: x",
        proposed_action={"tool_name": "flaky_thing", "arguments": {}},
    )
    response = client.post(f"/api/suggestions/{item.id}/accept")
    assert response.status_code == 409
    assert client.get("/api/inbox").json()["counts"] == {"open": 1}


def test_today_needs_you_merges_by_urgency_and_caps_at_three(api) -> None:
    client, container = api
    container.registry.register(_tool("send_thing", "execute", []))
    assert container.today.build(OWNER)["needs_you"] == []
    approval_id = _pending_approval(container)
    titles = ["One", "Two", "Three"]
    for title in titles:
        container.suggestions.create(
            OWNER, kind="idea", title=title, reason="r", source="tasks: list"
        )
    needs = client.get("/api/today").json()["needs_you"]
    assert len(needs) == 3
    assert needs[0]["kind"] == "approval" and needs[0]["id"] == approval_id
    assert all(item["kind"] == "suggestion" for item in needs[1:])
    assert all(item["source"] == "tasks: list" for item in needs[1:])
    assert "approval" not in needs[0] and "suggestion" not in needs[1]
    # The inbox still holds all four.
    assert client.get("/api/inbox").json()["counts"] == {"open": 4}


def test_expired_suggestions_leave_open_and_appear_done(api) -> None:
    client, container = api
    item = container.suggestions.create(
        OWNER,
        kind="idea",
        title="Gone soon",
        reason="r",
        source="calendar: today",
        expires_in=timedelta(seconds=-1),
    )
    assert client.get("/api/inbox").json()["items"] == []
    done = client.get("/api/inbox?tab=done").json()["items"]
    assert [(i["id"], i["status"]) for i in done] == [(item.id, "expired")]
