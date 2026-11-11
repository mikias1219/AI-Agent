"""/api/tasks views, filters, search, mutations and the minimal owner profile endpoints."""

from __future__ import annotations

import base64
import hashlib
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app

PASSWORD = "correct horse battery staple"
SALT = b"tasks-api-test-salt"


def _client(tmp_path) -> TestClient:
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'tasks-api.db'}",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    client = TestClient(
        create_dashboard_app(
            container=build_app(settings=settings, provider=FakeProvider()),
            frontend_dir=frontend,
        ),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client


def _make(client: TestClient, **body) -> dict:
    response = client.post("/api/tasks", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def _titles(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [t["title"] for t in response.json()]


def test_create_returns_p1_fields_and_resolves_plain_words(tmp_path):
    client = _client(tmp_path)

    task = _make(
        client,
        title="File taxes",
        notes="with receipts",
        priority="p1",
        due="friday 3pm",
        project="Home",
        tags=["money"],
    )

    assert task["priority"] == "p1"
    assert task["notes"] == task["description"] == "with receipts"
    assert task["project"] == "Home" and task["tags"] == ["money"]
    assert task["due_at"] is not None and task["completed_at"] is None
    assert task["source"] == "manual"


def test_views_split_tasks_by_due_date_without_overlap(tmp_path):
    client = _client(tmp_path)
    now = datetime.now(UTC)
    _make(client, title="late", due_at=(now - timedelta(days=2)).isoformat())
    _make(client, title="soon", due_at=(now + timedelta(days=3)).isoformat())
    _make(client, title="no due")
    done = _make(client, title="late but done", due_at=(now - timedelta(days=2)).isoformat())
    assert client.patch(f"/api/tasks/{done['id']}", json={"status": "done"}).status_code == 200

    assert _titles(client.get("/api/tasks", params={"view": "overdue"})) == ["late"]
    assert _titles(client.get("/api/tasks", params={"view": "upcoming"})) == ["soon"]
    assert _titles(client.get("/api/tasks", params={"view": "today"})) == []
    assert set(_titles(client.get("/api/tasks"))) == {"late", "soon", "no due", "late but done"}


def test_today_view_follows_owner_timezone(tmp_path):
    client = _client(tmp_path)
    assert client.get("/api/profile").json()["timezone"] == "UTC"
    updated = client.patch("/api/profile", json={"timezone": "Pacific/Auckland"})
    assert updated.status_code == 200 and updated.json()["timezone"] == "Pacific/Auckland"
    assert client.get("/api/profile").json()["timezone"] == "Pacific/Auckland"

    _make(client, title="tonight", due="today 11pm")

    assert _titles(client.get("/api/tasks", params={"view": "today"})) == ["tonight"]


def test_profile_rejects_unknown_timezone_and_bad_view(tmp_path):
    client = _client(tmp_path)

    assert client.patch("/api/profile", json={"timezone": "Mars/Base"}).status_code == 400
    assert client.get("/api/profile").json()["timezone"] == "UTC"
    assert client.get("/api/tasks", params={"view": "someday"}).status_code == 422
    assert client.post("/api/tasks", json={"title": "x", "due": "whenever"}).status_code == 400


def test_filters_and_search_combine(tmp_path):
    client = _client(tmp_path)
    _make(client, title="Pay rent", priority="p1", project="Home", tags=["money"])
    _make(client, title="Paint fence", priority="p3", project="Home", notes="blue paint")
    _make(client, title="Quarterly report", priority="p1", project="Work", tags=["money"])

    assert set(_titles(client.get("/api/tasks", params={"priority": "p1"}))) == {
        "Pay rent",
        "Quarterly report",
    }
    assert set(_titles(client.get("/api/tasks", params={"project": "home"}))) == {
        "Pay rent",
        "Paint fence",
    }
    assert set(_titles(client.get("/api/tasks", params={"tag": "money"}))) == {
        "Pay rent",
        "Quarterly report",
    }
    assert _titles(client.get("/api/tasks", params={"q": "paint blue"})) == ["Paint fence"]
    assert _titles(client.get("/api/tasks", params={"q": "money", "project": "Work"})) == [
        "Quarterly report"
    ]
    assert _titles(client.get("/api/tasks", params={"q": "nothing matches"})) == []
    assert _titles(client.get("/api/tasks", params={"status": "done"})) == []


def test_patch_updates_fields_clears_due_and_validates_transitions(tmp_path):
    client = _client(tmp_path)
    task = _make(client, title="Draft", due="tomorrow")
    url = f"/api/tasks/{task['id']}"

    edited = client.patch(url, json={"title": "Final", "priority": "p2", "tags": ["a"]}).json()
    assert (edited["title"], edited["priority"], edited["tags"]) == ("Final", "p2", ["a"])
    assert edited["due_at"] == task["due_at"]  # omitted -> unchanged

    assert client.patch(url, json={"due_at": None}).json()["due_at"] is None
    assert client.patch(url, json={"status": "done"}).json()["completed_at"] is not None
    assert client.patch(url, json={"status": "blocked"}).status_code == 400
    assert client.patch(url, json={"title": "   "}).status_code == 422
    assert client.patch("/api/tasks/missing", json={"title": "x"}).status_code == 404


def test_reopen_and_soft_delete_hide_from_default_lists(tmp_path):
    client = _client(tmp_path)
    task = _make(client, title="Ship it")
    url = f"/api/tasks/{task['id']}"
    client.patch(url, json={"status": "done"})

    reopened = client.post(f"{url}/reopen").json()
    assert reopened["status"] == "planned" and reopened["completed_at"] is None
    assert client.post(f"{url}/reopen").status_code == 400  # already planned

    assert client.delete(url).json() == {"id": task["id"], "deleted": True}
    assert client.delete(url).status_code == 200  # idempotent
    assert _titles(client.get("/api/tasks")) == []
    assert _titles(client.get("/api/tasks", params={"include_deleted": "true"})) == ["Ship it"]
    assert client.get(url).status_code == 404
    assert client.delete("/api/tasks/missing").status_code == 404
