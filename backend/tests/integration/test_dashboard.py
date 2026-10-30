"""Dashboard API and local approval handoff tests."""

from __future__ import annotations

import base64
import hashlib
import threading
import time

from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.domain.models import AssistantTurn, ToolCall, ToolSpec
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import DashboardApprovalNotifier, create_dashboard_app

TEST_PASSWORD = "correct horse battery staple"
TEST_SALT = b"dashboard-test-salt"
TEST_HASH = (
    base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", TEST_PASSWORD.encode(), TEST_SALT, 310_000)
    )
    .decode()
    .rstrip("=")
)


def _dashboard(tmp_path, extra_env=None, *, login=True):
    env = {
        "PERSONAL_AGENT_PROVIDER": "fake",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'dashboard.db'}",
        "DASHBOARD_PASSWORD_HASH": (
            f"{base64.urlsafe_b64encode(TEST_SALT).decode().rstrip('=')}${TEST_HASH}"
        ),
        "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
    }
    env.update(extra_env or {})
    settings = Settings.from_env(env)
    container = build_app(settings=settings, provider=FakeProvider())
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text(
        '<title>Personal Agent · Dashboard</title><div id="root"></div>'
    )
    client = TestClient(
        create_dashboard_app(container=container, frontend_dir=frontend),
        base_url="http://127.0.0.1",
    )
    if login:
        response = client.post("/api/login", json={"password": TEST_PASSWORD})
        assert response.status_code == 200
    return client


def test_dashboard_serves_local_page_and_status_without_secret(tmp_path):
    client = _dashboard(
        tmp_path,
        {"TELEGRAM_BOT_TOKEN": "secret-test-token", "TELEGRAM_ALLOWED_CHAT_IDS": "12345"},
    )

    page = client.get("/")
    status = client.get("/api/status").json()

    assert page.status_code == 200
    assert "Personal Agent · Dashboard" in page.text
    assert "Content-Security-Policy" in page.headers
    assert status["telegram"]["configured"] is True
    assert status["telegram"]["allowed_chat_ids"] == [12345]
    assert "secret-test-token" not in str(status)


def test_dashboard_requires_login_and_sets_secure_session_cookie(tmp_path):
    client = _dashboard(tmp_path, login=False)

    assert 'id="root"' in client.get("/").text
    assert client.get("/api/auth").json()["authenticated"] is False
    assert client.get("/api/status").status_code == 401
    assert client.post("/api/login", json={"password": "wrong"}).status_code == 401

    response = client.post("/api/login", json={"password": TEST_PASSWORD})

    assert response.status_code == 200
    assert response.cookies.get("personal_agent_session")
    assert "httponly" in response.headers["set-cookie"].lower()
    assert client.get("/api/status").status_code == 200
    assert client.post("/api/logout").status_code == 200
    assert client.get("/api/status").status_code == 401


def test_dashboard_chat_persists_conversation_history(tmp_path):
    client = _dashboard(tmp_path)

    response = client.post("/api/chat", json={"text": "hello"})
    session_id = response.json()["session_id"]
    conversations = client.get("/api/conversations").json()
    messages = client.get(f"/api/conversations/{session_id}/messages").json()
    events = client.get("/api/activity?limit=10").json()

    assert response.status_code == 200
    assert response.json()["reply"] == "Okay."
    assert conversations[0]["id"] == session_id
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert {event["event"] for event in events} >= {
        "conversation.session_created",
        "chat.user_message",
        "chat.assistant_response",
    }


def test_dashboard_activity_paginates_all_recorded_actions(tmp_path):
    client = _dashboard(tmp_path)
    task = client.post("/api/tasks", json={"title": "Activity task"}).json()
    client.patch(f"/api/tasks/{task['id']}", json={"status": "in_progress"})

    latest = client.get("/api/activity?limit=1&offset=0").json()
    earlier = client.get("/api/activity?limit=1&offset=1").json()
    all_events = client.get("/api/activity?limit=100").json()

    assert latest[0]["event"] == "task.status_changed"
    assert earlier[0]["event"] == "task.created"
    assert len(all_events) >= 2


def test_dashboard_task_routes_use_domain_transitions(tmp_path):
    client = _dashboard(tmp_path)

    created = client.post("/api/tasks", json={"title": "Prepare demo"})
    task = created.json()
    rejected = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "done"},
    )
    updated = client.patch(
        f"/api/tasks/{task['id']}",
        json={"status": "in_progress"},
    )

    assert created.status_code == 201
    assert rejected.status_code == 400
    assert updated.json()["status"] == "in_progress"


def test_dashboard_rejects_cross_origin_browser_requests(tmp_path):
    client = _dashboard(tmp_path)

    response = client.post(
        "/api/tasks",
        headers={"Origin": "https://example.com"},
        json={"title": "Not accepted"},
    )

    assert response.status_code == 403


def test_approval_notifier_resolves_live_waiter_once():
    notifier = DashboardApprovalNotifier(timeout_seconds=2)
    decisions: list[tuple[str, bool]] = []
    notifier.bind_decider(lambda approval_id, approve: decisions.append((approval_id, approve)))
    result: list[str] = []
    entered = threading.Event()

    def wait_for_approval():
        entered.set()
        result.append(notifier("Approve this?", {"approval_id": "approval-1"}))

    worker = threading.Thread(target=wait_for_approval)
    worker.start()
    assert entered.wait(timeout=1)
    deadline = time.monotonic() + 1
    while not notifier.is_waiting("approval-1") and time.monotonic() < deadline:
        time.sleep(0.005)
    assert notifier.is_waiting("approval-1")

    assert notifier.resolve("approval-1", True) == "approved"
    worker.join(timeout=1)

    assert not worker.is_alive()
    assert result == ["approved"]
    assert decisions == [("approval-1", True)]


def test_dashboard_approval_continues_the_waiting_chat_turn(tmp_path):
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'approval.db'}",
            "APPROVAL_TIMEOUT_SECONDS": "3",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(TEST_SALT).decode().rstrip('=')}${TEST_HASH}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    provider = FakeProvider(
        [
            AssistantTurn(
                tool_calls=(
                    ToolCall(id="call-1", name="protected_action", arguments={"value": "ok"}),
                )
            ),
            AssistantTurn(content="Action completed."),
        ]
    )
    notifier = DashboardApprovalNotifier(timeout_seconds=3)
    container = build_app(
        settings=settings,
        provider=provider,
        approval_notifier=notifier,
    )
    executed: list[tuple[str, str]] = []
    container.registry.register(
        ToolSpec(
            name="protected_action",
            description="An action requiring approval",
            parameters_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
                "additionalProperties": False,
            },
            access_kind="execute",
            handler=lambda ctx, args: executed.append((ctx.origin, args["value"])) or "done",
        )
    )
    client = TestClient(
        create_dashboard_app(container=container, approval_notifier=notifier),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": TEST_PASSWORD}).status_code == 200
    chat_result = []
    chat_thread = threading.Thread(
        target=lambda: chat_result.append(client.post("/api/chat", json={"text": "do it"}))
    )
    chat_thread.start()

    deadline = time.monotonic() + 2
    pending = []
    while time.monotonic() < deadline:
        pending = client.get("/api/approvals").json()
        if pending:
            break
        time.sleep(0.01)
    assert len(pending) == 1
    assert pending[0]["actionable"] is True
    decision = client.post(
        f"/api/approvals/{pending[0]['id']}/decision",
        json={"approve": True},
    )
    chat_thread.join(timeout=2)

    assert decision.status_code == 200
    assert not chat_thread.is_alive()
    assert chat_result[0].json()["reply"] == "Action completed."
    assert executed == [("dashboard", "ok")]
    assert client.get("/api/approvals").json() == []


def test_workspace_registration_persists_owner_and_requires_real_login(tmp_path):
    client = _dashboard(tmp_path, {"DASHBOARD_PASSWORD_HASH": ""}, login=False)
    assert client.get("/api/auth").json()["registered"] is False
    registered = client.post(
        "/api/register",
        json={"name": "Mikias", "email": "owner@example.com", "password": "a-private-password"},
    )
    assert registered.status_code == 201
    assert (
        client.post(
            "/api/register",
            json={"name": "Other", "email": "other@example.com", "password": "another-password"},
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/login", json={"email": "wrong@example.com", "password": "a-private-password"}
        ).status_code
        == 401
    )
    assert (
        client.post(
            "/api/login", json={"email": "owner@example.com", "password": "a-private-password"}
        ).status_code
        == 200
    )
    assert client.get("/api/auth").json()["user"]["name"] == "Mikias"
    assert "password" not in client.get("/api/auth").text
    # Recreate the app against the same DB: account and password survive restart.
    restarted = _dashboard(tmp_path, {"DASHBOARD_PASSWORD_HASH": ""}, login=False)
    assert restarted.get("/api/auth").json()["registered"] is True
    assert (
        restarted.post(
            "/api/login", json={"email": "owner@example.com", "password": "a-private-password"}
        ).status_code
        == 200
    )
    restarted.app.state.container.auth.reset_password("a-different-password")
    assert restarted.get("/api/status").status_code == 401
    assert (
        restarted.post(
            "/api/login", json={"email": "owner@example.com", "password": "a-different-password"}
        ).status_code
        == 200
    )


def test_react_shell_and_assets_are_public_but_agent_data_is_private(tmp_path):
    build = tmp_path / "frontend"
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text('<div id="root"></div>')
    (build / "assets" / "app.js").write_text('console.log("app")')
    legacy = _dashboard(tmp_path, login=False)
    client = TestClient(
        create_dashboard_app(container=legacy.app.state.container, frontend_dir=build),
        base_url="http://127.0.0.1",
    )
    assert 'id="root"' in client.get("/").text
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/api/conversations").status_code == 401
    assert client.post("/api/telegram/start").status_code == 401
    assert client.get("/api/auth").headers["cache-control"] == "no-store"


def test_telegram_runtime_and_verification_are_real_and_do_not_send(tmp_path):
    client = _dashboard(
        tmp_path, {"TELEGRAM_BOT_TOKEN": "123:test", "TELEGRAM_ALLOWED_CHAT_IDS": "42"}
    )
    container = client.app.state.container

    class Identity:
        def get_me(self):
            return {"id": 123, "username": "test_bot", "first_name": "My bot"}

    from personal_agent.application.services.telegram_service import TelegramService

    container.telegram = TelegramService(Identity())
    assert client.post("/api/telegram/verify").json()["username"] == "test_bot"
    container.audit.record(
        "telegram.runtime", "telegram", {"phase": "polling", "username": "test_bot"}
    )
    status = client.get("/api/status").json()["telegram"]
    assert status["runtime"] == "polling"
    assert status["username"] == "test_bot"
    assert status["managed"] is False
    # Do not create a second poller when the CLI bot is active.
    assert client.post("/api/telegram/start").status_code == 409
    assert "123:test" not in client.get("/api/status").text
    assert client.get("/api/telegram/activity").json()[0]["event"] == "telegram.identity_verified"


def test_missing_frontend_build_has_clear_error_without_breaking_api(tmp_path):
    client = _dashboard(tmp_path, login=False)
    app = create_dashboard_app(
        container=client.app.state.container, frontend_dir=tmp_path / "missing-build"
    )
    missing = TestClient(app, base_url="http://127.0.0.1")
    assert missing.get("/").status_code == 503
    assert "npm --prefix frontend run build" in missing.get("/").json()["detail"]
    assert missing.get("/api/auth").status_code == 200


def test_frontend_can_be_built_after_backend_startup(tmp_path):
    baseline = _dashboard(tmp_path, login=False)
    build = tmp_path / "later-build"
    client = TestClient(
        create_dashboard_app(container=baseline.app.state.container, frontend_dir=build),
        base_url="http://127.0.0.1",
    )
    assert client.get("/").status_code == 503
    (build / "assets").mkdir(parents=True)
    (build / "index.html").write_text('<div id="root"></div>')
    (build / "assets" / "app.js").write_text("export const ready = true;")
    (build / "private.env").write_text("not-public")
    assert client.get("/").status_code == 200
    assert client.get("/assets/app.js").status_code == 200
    assert client.get("/assets/%2E%2E%2Fprivate.env").status_code == 404


def test_streaming_chat_finishes_with_persisted_final_answer(tmp_path):
    import json

    client = _dashboard(tmp_path)
    response = client.post("/api/chat/stream", json={"text": "hello"})
    frames = [json.loads(line) for line in response.text.splitlines()]
    assert response.status_code == 200
    assert frames[0] == {"type": "delta", "text": "Okay."}
    assert frames[-1]["type"] == "done"
    assert frames[-1]["reply"] == "Okay."
    session_id = frames[-1]["session_id"]
    history = client.get(f"/api/conversations/{session_id}/messages").json()
    assert history[-1]["content"] == "Okay."
    assert client.post("/api/logout").status_code == 200
    assert client.post("/api/chat/stream", json={"text": "not allowed"}).status_code == 401
