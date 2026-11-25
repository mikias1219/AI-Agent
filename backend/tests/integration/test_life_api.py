"""Life API (docs/LIFE_API_CONTRACT.md): endpoints, limits, profile, password, export, wipe."""

from __future__ import annotations

import base64
import hashlib

import pytest
from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app

PASSWORD = "correct horse battery staple"
SALT = b"life-test-salt"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32


def b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _hash(password: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), SALT, 310_000)
    salt = base64.urlsafe_b64encode(SALT).decode().rstrip("=")
    return f"{salt}${base64.urlsafe_b64encode(digest).decode().rstrip('=')}"


def _build(tmp_path, *, register: bool = False):
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'life.db'}",
            "DASHBOARD_PASSWORD_HASH": _hash(PASSWORD),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    container = build_app(settings=settings, provider=FakeProvider())
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    app = create_dashboard_app(container=container, frontend_dir=frontend)
    return container, app


@pytest.fixture()
def env(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # login lockout file lives under ./data
    container, app = _build(tmp_path)
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return container, client


@pytest.fixture()
def client(env):
    return env[1]


# -- notes and diary ---------------------------------------------------------------------------


def test_requires_login(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    _, app = _build(tmp_path)
    anon = TestClient(app, base_url="http://127.0.0.1")
    for path in ("/api/notes", "/api/files", "/api/learn/items", "/api/reading/plans"):
        assert anon.get(path).status_code == 401
    assert anon.get("/api/profile/photo").status_code == 401


def test_note_crud_search_and_ordering(client) -> None:
    first = client.post(
        "/api/notes", json={"kind": "note", "title": "Alpha", "body": "buy milk", "tags": ["Home"]}
    )
    assert first.status_code == 201
    note = first.json()
    assert note["kind"] == "note" and note["tags"] == ["home"] and note["mood"] is None
    assert note["entry_date"] is None and note["pinned"] is False and len(note["id"]) == 32
    client.post(
        "/api/notes", json={"kind": "note", "title": "Beta", "body": "call Sam", "pinned": True}
    )
    client.post("/api/notes", json={"kind": "note", "body": "# Derived title\nbody"})

    listed = client.get("/api/notes", params={"kind": "note"}).json()
    assert [n["title"] for n in listed][0] == "Beta"  # pinned first
    assert listed[1]["title"] == "Derived title"  # then newest
    assert [n["title"] for n in client.get("/api/notes", params={"q": "MILK"}).json()] == ["Alpha"]
    assert len(client.get("/api/notes", params={"tag": "home"}).json()) == 1
    assert len(client.get("/api/notes", params={"limit": 1, "offset": 1}).json()) == 1

    got = client.get(f"/api/notes/{note['id']}")
    assert got.status_code == 200
    patched = client.patch(
        f"/api/notes/{note['id']}", json={"body": "buy oat milk", "pinned": True}
    )
    assert patched.json()["body"] == "buy oat milk" and patched.json()["pinned"] is True
    assert client.delete(f"/api/notes/{note['id']}").status_code == 204
    assert client.get(f"/api/notes/{note['id']}").status_code == 404
    assert client.delete(f"/api/notes/{note['id']}").status_code == 404


def test_note_validation_is_400(client) -> None:
    assert client.post("/api/notes", json={"kind": "other", "body": "x"}).status_code == 400
    assert client.post("/api/notes", json={"kind": "note", "body": "x" * 50_001}).status_code == 400
    assert (
        client.post("/api/notes", json={"kind": "note", "body": "x", "mood": "good"}).status_code
        == 400
    )
    assert (
        client.post(
            "/api/notes", json={"kind": "note", "body": "x", "tags": [f"t{i}" for i in range(11)]}
        ).status_code
        == 400
    )
    assert client.get("/api/notes", params={"limit": 500}).status_code == 400
    assert client.get("/api/notes", params={"kind": "x"}).status_code == 400
    assert client.get("/api/notes", params={"offset": -1}).status_code == 400
    assert client.get("/api/notes/nope").status_code == 404


def test_diary_one_entry_per_date_and_stats(client) -> None:
    created = client.post(
        "/api/notes",
        json={"kind": "diary", "body": "Good day", "mood": "great", "entry_date": "2026-01-05"},
    )
    assert created.status_code == 201
    assert created.json()["entry_date"] == "2026-01-05" and created.json()["mood"] == "great"
    dup = client.post(
        "/api/notes", json={"kind": "diary", "body": "again", "entry_date": "2026-01-05"}
    )
    assert dup.status_code == 409
    assert dup.json() == {"detail": "A diary entry for this date already exists."}
    today_entry = client.post("/api/notes", json={"kind": "diary", "body": "today"})
    assert today_entry.status_code == 201 and today_entry.json()["entry_date"]
    client.post("/api/notes", json={"kind": "diary", "body": "older", "entry_date": "2026-01-04"})
    diary = client.get("/api/notes", params={"kind": "diary"}).json()
    dates = [d["entry_date"] for d in diary]
    assert dates == sorted(dates, reverse=True)
    other = client.post(
        "/api/notes", json={"kind": "diary", "body": "x", "entry_date": "2026-01-04"}
    )
    assert other.status_code == 409
    moved = client.patch(f"/api/notes/{created.json()['id']}", json={"entry_date": "2026-01-04"})
    assert moved.status_code == 409
    stats = client.get("/api/notes/stats").json()
    assert stats["diary_entries"] == 3 and stats["notes"] == 0
    assert stats["wrote_diary_today"] is True and stats["diary_streak_days"] >= 1
    assert (
        client.post(
            "/api/notes", json={"kind": "diary", "body": "x", "entry_date": "2026-13-40"}
        ).status_code
        == 400
    )


# -- files -------------------------------------------------------------------------------------


def _upload(client, name="a.txt", mime="text/plain", data=b"hello", **extra):
    return client.post(
        "/api/files", json={"name": name, "mime": mime, "data_base64": b64(data), **extra}
    )


def test_file_upload_list_content_and_stats(client) -> None:
    text = _upload(client, description="Greeting", tags=["Docs"])
    assert text.status_code == 201
    item = text.json()
    assert (
        item["kind"] == "file"
        and item["size"] == 5
        and item["url"] == f"/api/files/{item['id']}/content"
    )
    image = _upload(client, name="p.png", mime="image/png", data=PNG).json()
    assert image["kind"] == "image"

    content = client.get(item["url"])
    assert content.content == b"hello" and content.headers["content-type"].startswith("text/plain")
    assert content.headers["x-content-type-options"] == "nosniff"
    assert content.headers["content-disposition"].startswith("attachment; filename=")
    inline = client.get(image["url"])
    assert inline.headers["content-disposition"] == "inline" and inline.content == PNG

    assert [f["name"] for f in client.get("/api/files", params={"kind": "image"}).json()] == [
        "p.png"
    ]
    assert len(client.get("/api/files", params={"q": "greet"}).json()) == 1
    assert len(client.get("/api/files", params={"tag": "docs"}).json()) == 1
    assert client.get("/api/files/stats").json() == {"files": 1, "images": 1, "bytes": 5 + len(PNG)}

    patched = client.patch(
        f"/api/files/{item['id']}", json={"name": "b.txt", "description": "x", "tags": ["z"]}
    )
    assert patched.json()["name"] == "b.txt" and patched.json()["tags"] == ["z"]
    assert client.delete(f"/api/files/{item['id']}").status_code == 204
    assert client.get(item["url"]).status_code == 404


def test_file_limits_and_type_checks(client) -> None:
    assert _upload(client, data=b"x" * (5 * 1024 * 1024 + 1)).status_code == 413
    assert _upload(client, data=b"x" * (5 * 1024 * 1024)).status_code == 201
    assert _upload(client, name="x.svg", mime="image/svg+xml", data=b"<svg/>").status_code == 415
    assert _upload(client, name="x.bin", mime="application/octet-stream").status_code == 415
    assert _upload(client, name="x.png", mime="image/png", data=JPEG).status_code == 415
    assert _upload(client, name="x.pdf", mime="application/pdf", data=b"<html>").status_code == 415
    assert _upload(client, name="x.txt", data=b"a\x00b").status_code == 415
    assert _upload(client, name="", data=b"x").status_code == 400
    assert (
        client.post(
            "/api/files", json={"name": "a", "mime": "text/plain", "data_base64": "!!!"}
        ).status_code
        == 400
    )
    assert client.post("/api/files", json={"name": "a", "mime": "text/plain"}).status_code == 400
    assert (
        _upload(client, name="ok.pdf", mime="application/pdf", data=b"%PDF-1.4 x").status_code
        == 201
    )


def test_owner_storage_cap(env) -> None:
    container, client = env
    container.files._cap = 100  # noqa: SLF001 - shrink the 200 MB cap for the test
    assert _upload(client, data=b"x" * 60).status_code == 201
    full = _upload(client, name="b.txt", data=b"y" * 60)
    assert full.status_code == 413 and full.json() == {"detail": "Storage limit reached."}


def test_file_name_cannot_inject_headers(client) -> None:
    item = _upload(client, name='../ev"il\r\nX-Evil: 1.txt').json()
    assert "/" not in item["name"] and "\n" not in item["name"]
    disposition = client.get(item["url"]).headers["content-disposition"]
    assert "\n" not in disposition and "x-evil" not in client.get(item["url"]).headers


# -- learning ----------------------------------------------------------------------------------


def test_learn_create_review_and_stats(client) -> None:
    single = client.post(
        "/api/learn/items",
        json={
            "term": "Hola",
            "meaning": "hello",
            "example": "Hola!",
            "language": "es",
            "topic": "basics",
        },
    )
    assert single.status_code == 201 and len(single.json()) == 1
    item = single.json()[0]
    assert item["box"] == 0 and item["times_correct"] == 0 and item["kind"] == "word"

    batch = client.post(
        "/api/learn/items",
        json={
            "items": [
                {"term": "hola", "meaning": "dup", "language": "es"},  # duplicate, case-insensitive
                {"term": "HOLA", "meaning": "dup in same language, other case", "language": "es"},
                {"term": "hola", "meaning": "same term other language", "language": "pt"},
                {"term": "gracias", "meaning": "thanks", "language": "es", "topic": "basics"},
            ]
        },
    )
    assert batch.status_code == 201
    assert sorted(i["term"] for i in batch.json()) == ["gracias", "hola"]
    assert (
        client.post(
            "/api/learn/items",
            json={"items": [{"term": f"w{i}", "meaning": "m"} for i in range(21)]},
        ).status_code
        == 400
    )
    assert client.post("/api/learn/items", json={"term": "", "meaning": "m"}).status_code == 400

    assert len(client.get("/api/learn/items", params={"due": "true"}).json()) == 3
    assert client.get("/api/learn/topics").json() == ["basics"]
    assert len(client.get("/api/learn/items", params={"topic": "basics"}).json()) == 2
    assert len(client.get("/api/learn/items", params={"language": "pt"}).json()) == 1
    assert len(client.get("/api/learn/items", params={"q": "THANK"}).json()) == 1

    know = client.post(f"/api/learn/items/{item['id']}/review", json={"result": "know"}).json()
    assert know["box"] == 1 and know["times_correct"] == 1
    assert (
        len(client.get("/api/learn/items", params={"due": "true"}).json()) == 2
    )  # now due tomorrow
    again = client.post(f"/api/learn/items/{item['id']}/review", json={"result": "again"}).json()
    assert again["box"] == 0 and again["times_wrong"] == 1
    assert (
        client.post(f"/api/learn/items/{item['id']}/review", json={"result": "x"}).status_code
        == 400
    )
    assert client.post("/api/learn/items/nope/review", json={"result": "know"}).status_code == 404

    stats = client.get("/api/learn/stats").json()
    assert stats["total"] == 3 and stats["reviewed_today"] == 2 and stats["streak_days"] == 1
    assert stats["learned"] == 0 and stats["due"] >= 2

    patched = client.patch(f"/api/learn/items/{item['id']}", json={"meaning": "hi"})
    assert patched.json()["meaning"] == "hi"
    clash = client.patch(f"/api/learn/items/{item['id']}", json={"term": "gracias"})
    assert clash.status_code == 409
    assert client.delete(f"/api/learn/items/{item['id']}").status_code == 204
    assert client.delete(f"/api/learn/items/{item['id']}").status_code == 404


def test_learned_counts_box_three_and_up(env) -> None:
    _, client = env
    item = client.post("/api/learn/items", json={"term": "a", "meaning": "b"}).json()[0]
    for _ in range(3):
        last = client.post(f"/api/learn/items/{item['id']}/review", json={"result": "know"}).json()
    assert last["box"] == 3
    assert client.get("/api/learn/stats").json()["learned"] == 1


# -- reading -----------------------------------------------------------------------------------


def test_reading_plans_templates_advance_and_logs(client) -> None:
    templates = client.get("/api/reading/templates").json()
    assert {t["id"] for t in templates} == {
        "gospel-of-john-21",
        "psalms-30",
        "proverbs-31",
        "new-testament-90",
    }
    assert next(t for t in templates if t["id"] == "new-testament-90")["count"] == 90

    created = client.post(
        "/api/reading/plans", json={"name": "John", "template": "gospel-of-john-21"}
    )
    assert created.status_code == 201
    plan = created.json()
    assert plan["items"][0] == "John 1" and plan["position"] == 0 and plan["next"] == "John 1"
    assert plan["progress"] == 0.0 and plan["active"] is True

    wins = client.post(
        "/api/reading/plans",
        json={"name": "Mine", "items": ["A 1", "A 2"], "template": "psalms-30"},
    )
    assert wins.json()["items"] == ["A 1", "A 2"]  # items win over template
    assert (
        client.post("/api/reading/plans", json={"name": "x", "template": "nope"}).status_code == 400
    )
    assert client.post("/api/reading/plans", json={"name": "", "items": ["a"]}).status_code == 400
    assert (
        client.post("/api/reading/plans", json={"name": "x", "items": ["a"] * 1501}).status_code
        == 400
    )

    small = wins.json()
    first = client.post(f"/api/reading/plans/{small['id']}/advance", json={"reflection": "Calm"})
    assert first.status_code == 200
    body = first.json()
    assert body["log"]["reference"] == "A 1" and body["log"]["reflection"] == "Calm"
    assert body["log"]["plan_id"] == small["id"] and body["plan"]["position"] == 1
    assert body["plan"]["progress"] == 0.5 and body["plan"]["next"] == "A 2"
    done = client.post(f"/api/reading/plans/{small['id']}/advance").json()
    assert done["plan"]["next"] is None and done["plan"]["progress"] == 1.0
    past = client.post(f"/api/reading/plans/{small['id']}/advance", json={})
    assert past.status_code == 409

    assert (
        client.patch(f"/api/reading/plans/{plan['id']}", json={"position": 99}).status_code == 400
    )
    moved = client.patch(
        f"/api/reading/plans/{plan['id']}", json={"position": 3, "name": "John 2", "active": False}
    )
    assert moved.json()["next"] == "John 4" and moved.json()["active"] is False

    manual = client.post(
        "/api/reading/logs",
        json={
            "reference": "Psalm 23",
            "reflection": "Peace",
            "read_on": "2026-01-02",
            "plan_id": plan["id"],
        },
    )
    assert manual.status_code == 201 and manual.json()["read_on"] == "2026-01-02"
    assert (
        client.post("/api/reading/logs", json={"reference": "x", "plan_id": "nope"}).status_code
        == 404
    )
    assert client.post("/api/reading/logs", json={"reference": ""}).status_code == 400
    assert (
        client.post("/api/reading/logs", json={"reference": "x", "read_on": "bad"}).status_code
        == 400
    )
    assert len(client.get("/api/reading/logs", params={"plan_id": plan["id"]}).json()) == 1
    assert len(client.get("/api/reading/logs").json()) == 3
    log_id = manual.json()["id"]
    assert (
        client.patch(f"/api/reading/logs/{log_id}", json={"reflection": "More"}).json()[
            "reflection"
        ]
        == "More"
    )
    assert client.delete(f"/api/reading/logs/{log_id}").status_code == 204
    assert client.delete(f"/api/reading/logs/{log_id}").status_code == 404

    stats = client.get("/api/reading/stats").json()
    assert stats["logs"] == 2 and stats["read_today"] is True and stats["streak_days"] == 1
    assert stats["active_plan"] is None  # John plan deactivated, small plan finished
    client.patch(f"/api/reading/plans/{plan['id']}", json={"active": True})
    assert client.get("/api/reading/stats").json()["active_plan"]["id"] == plan["id"]
    assert client.delete(f"/api/reading/plans/{plan['id']}").status_code == 204
    assert client.get("/api/reading/stats").json()["active_plan"] is None


# -- profile -----------------------------------------------------------------------------------


def test_profile_extensions_and_photo(client) -> None:
    profile = client.get("/api/profile").json()
    assert profile["bio"] == "" and profile["birthday"] is None and profile["has_photo"] is False
    assert profile["photo_url"] is None and profile["member_since"]
    patched = client.patch(
        "/api/profile",
        json={"bio": "Hello", "birthday": "1990-04-02", "timezone": "Africa/Nairobi"},
    )
    assert patched.status_code == 200 and patched.json()["bio"] == "Hello"
    assert (
        patched.json()["birthday"] == "1990-04-02"
        and patched.json()["timezone"] == "Africa/Nairobi"
    )
    assert client.patch("/api/profile", json={"timezone": "Mars/Base"}).status_code == 400
    assert client.patch("/api/profile", json={"bio": "x" * 501}).status_code == 400
    assert client.patch("/api/profile", json={"birthday": "nope"}).status_code == 400
    assert client.patch("/api/profile", json={"birthday": None}).json()["birthday"] is None

    assert client.get("/api/profile/photo").status_code == 404
    assert (
        client.put(
            "/api/profile/photo", json={"mime": "image/gif", "data_base64": b64(b"GIF89a....")}
        ).status_code
        == 415
    )
    assert (
        client.put(
            "/api/profile/photo", json={"mime": "image/png", "data_base64": b64(JPEG)}
        ).status_code
        == 415
    )
    assert (
        client.put(
            "/api/profile/photo",
            json={"mime": "image/png", "data_base64": b64(PNG + b"x" * 1024 * 1024)},
        ).status_code
        == 413
    )
    ok = client.put("/api/profile/photo", json={"mime": "image/png", "data_base64": b64(PNG)})
    assert ok.status_code == 200 and ok.json() == {"photo_url": "/api/profile/photo"}
    assert client.get("/api/profile").json()["photo_url"] == "/api/profile/photo"
    photo = client.get("/api/profile/photo")
    assert photo.content == PNG and photo.headers["x-content-type-options"] == "nosniff"
    assert photo.headers["cache-control"] == "private, max-age=0, must-revalidate"
    cached = client.get("/api/profile/photo", headers={"If-None-Match": photo.headers["etag"]})
    assert cached.status_code == 304
    assert client.get("/api/files").json() == []  # photo is not in the Library
    assert client.delete("/api/profile/photo").status_code == 204
    assert client.get("/api/profile").json()["has_photo"] is False
    assert client.get("/api/profile/photo").status_code == 404


# -- password ----------------------------------------------------------------------------------


def _register_and_login(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'acct.db'}",
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    container = build_app(settings=settings, provider=FakeProvider())
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text("<div></div>")
    app = create_dashboard_app(container=container, frontend_dir=frontend)

    def new_client() -> TestClient:
        return TestClient(app, base_url="http://127.0.0.1")

    first = new_client()
    reg = first.post(
        "/api/register",
        json={"name": "Sam", "email": "sam@example.com", "password": "old-password-123"},
    )
    assert reg.status_code == 201
    login = {"password": "old-password-123", "email": "sam@example.com"}
    assert first.post("/api/login", json=login).status_code == 200
    second = new_client()
    assert second.post("/api/login", json=login).status_code == 200
    return container, first, second, new_client


def test_password_change_rotates_sessions_and_audits(tmp_path, monkeypatch) -> None:
    container, first, second, new_client = _register_and_login(tmp_path, monkeypatch)
    profile = first.get("/api/profile").json()
    assert profile["email"] == "sam@example.com"

    wrong = first.post(
        "/api/auth/password",
        json={"current_password": "nope", "new_password": "a-brand-new-pass-1"},
    )
    assert wrong.status_code == 401 and wrong.json() == {"detail": "Current password is incorrect."}
    short = first.post(
        "/api/auth/password", json={"current_password": "old-password-123", "new_password": "short"}
    )
    assert short.status_code == 400
    long = first.post(
        "/api/auth/password",
        json={"current_password": "old-password-123", "new_password": "x" * 129},
    )
    assert long.status_code == 400
    same = first.post(
        "/api/auth/password",
        json={"current_password": "old-password-123", "new_password": "old-password-123"},
    )
    assert same.status_code == 400  # 16 chars but identical

    done = first.post(
        "/api/auth/password",
        json={"current_password": "old-password-123", "new_password": "a-brand-new-pass-1"},
    )
    assert done.status_code == 204 and done.content == b""
    assert "personal_agent_session" in done.headers.get("set-cookie", "")
    assert first.get("/api/profile").status_code == 200  # this browser stays signed in
    assert second.get("/api/profile").status_code == 401  # others are signed out

    fresh = new_client()
    old = {"password": "old-password-123", "email": "sam@example.com"}
    assert fresh.post("/api/login", json=old).status_code == 401
    new = {"password": "a-brand-new-pass-1", "email": "sam@example.com"}
    assert fresh.post("/api/login", json=new).status_code == 200

    events = container.audit.list_recent(limit=20, events=["auth.password_changed"])
    assert len(events) == 1
    assert "a-brand-new-pass-1" not in str(events) and "old-password-123" not in str(events)


def test_password_change_is_rate_limited_like_login(tmp_path, monkeypatch) -> None:
    _, first, _, _ = _register_and_login(tmp_path, monkeypatch)
    body = {"current_password": "wrong", "new_password": "a-brand-new-pass-1"}
    codes = [first.post("/api/auth/password", json=body).status_code for _ in range(6)]
    assert codes[:5] == [401] * 5 and codes[5] == 429
    good = {"current_password": "old-password-123", "new_password": "a-brand-new-pass-1"}
    assert first.post("/api/auth/password", json=good).status_code == 429


def test_password_managed_in_env_cannot_change(client) -> None:
    resp = client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": "a-brand-new-pass-1"},
    )
    assert resp.status_code == 409


# -- notifications -----------------------------------------------------------------------------


def test_notification_prefs_roundtrip_and_enforced(env) -> None:
    container, client = env
    prefs = client.get("/api/profile/notifications").json()
    assert prefs["channels"] == {"in_app": True, "telegram": True}
    assert prefs["daily_briefing"] is True and prefs["learning_daily"] is False
    assert prefs["quiet_hours"] == {"enabled": False, "start": "22:00", "end": "07:00"}
    assert set(prefs["enforced"]) == {
        "channels",
        "daily_briefing",
        "reminders",
        "learning_daily",
        "reading_daily",
        "diary_nudge",
        "learning_time",
        "reading_time",
        "diary_time",
        "daily_wrapup",
        "wrapup_time",
        "quiet_hours",
    }
    assert prefs["daily_wrapup"] is False and prefs["wrapup_time"] == "21:00"

    patched = client.patch(
        "/api/profile/notifications",
        json={
            "learning_daily": True,
            "learning_time": "18:30",
            "daily_briefing": False,
            "reminders": False,
            "channels": {"telegram": False},
            "quiet_hours": {"enabled": True, "start": "23:00"},
        },
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["learning_daily"] is True and body["learning_time"] == "18:30"
    assert body["daily_briefing"] is False and body["reminders"] is False
    assert body["channels"] == {"in_app": True, "telegram": False}
    assert body["quiet_hours"] == {"enabled": True, "start": "23:00", "end": "07:00"}
    # The flags drive the real routines.
    autos = {a.kind: a for a in container.automations.list("dashboard")}
    assert autos["learning_daily"].enabled and autos["learning_daily"].schedule_time == "18:30"
    assert not autos["daily_briefing"].enabled
    assert client.get("/api/profile/notifications").json()["learning_time"] == "18:30"

    assert (
        client.patch("/api/profile/notifications", json={"learning_time": "25:00"}).status_code
        == 400
    )
    assert client.patch("/api/profile/notifications", json={"reminders": "yes"}).status_code == 400
    assert (
        client.patch("/api/profile/notifications", json={"channels": {"in_app": 1}}).status_code
        == 400
    )


# -- today -------------------------------------------------------------------------------------


def test_today_life_object_absent_until_used(client) -> None:
    assert "life" not in client.get("/api/today").json()
    client.post("/api/learn/items", json={"term": "hola", "meaning": "hello"})
    client.post("/api/reading/plans", json={"name": "John", "template": "gospel-of-john-21"})
    client.post("/api/notes", json={"kind": "note", "title": "N1", "body": "b"})
    life = client.get("/api/today").json()["life"]
    assert life["learn"] == {"due": 1, "total": 1, "next_term": "hola"}
    assert life["reading"] == {
        "next": "John 1",
        "plan_name": "John",
        "read_today": False,
        "streak_days": 0,
    }
    assert life["diary"] == {"wrote_today": False, "streak_days": 0}
    assert [n["title"] for n in life["notes"]["recent"]] == ["N1"]
    client.post("/api/notes", json={"kind": "diary", "body": "x"})
    assert client.get("/api/today").json()["life"]["diary"] == {
        "wrote_today": True,
        "streak_days": 1,
    }


# -- export and wipe ---------------------------------------------------------------------------


def test_export_and_wipe_cover_every_life_table(client) -> None:
    client.post("/api/notes", json={"kind": "note", "title": "N", "body": "b"})
    client.post("/api/notes", json={"kind": "diary", "body": "d"})
    _upload(client)
    item = client.post("/api/learn/items", json={"term": "a", "meaning": "b"}).json()[0]
    client.post(f"/api/learn/items/{item['id']}/review", json={"result": "know"})
    plan = client.post("/api/reading/plans", json={"name": "P", "items": ["A 1"]}).json()
    client.post(f"/api/reading/plans/{plan['id']}/advance")
    client.put("/api/profile/photo", json={"mime": "image/png", "data_base64": b64(PNG)})
    client.patch("/api/profile", json={"bio": "About me", "birthday": "1990-01-01"})

    data = client.get("/api/export").json()
    assert len(data["notes"]) == 2 and {n["kind"] for n in data["notes"]} == {"note", "diary"}
    assert base64.b64decode(data["files"][0]["data_base64"]) == b"hello"
    assert len(data["learn_items"]) == 1 and len(data["learn_reviews"]) == 1
    assert len(data["reading_plans"]) == 1 and len(data["reading_logs"]) == 1
    assert base64.b64decode(data["profile_photo"]["data_base64"]) == PNG
    assert data["profile"]["bio"] == "About me" and data["profile"]["birthday"] == "1990-01-01"

    token = client.post("/api/workspace/wipe/token").json()
    wiped = client.post(
        "/api/workspace/wipe",
        json={"token": token["token"], "confirm_phrase": token["confirm_phrase"]},
    )
    assert wiped.status_code == 200
    deleted = wiped.json()["deleted"]
    assert deleted["notes"] == 2 and deleted["files"] == 1 and deleted["learn_items"] == 1
    assert deleted["reading_plans"] == 1 and deleted["profile_photo"] == 1

    assert client.get("/api/notes").json() == []
    assert client.get("/api/files").json() == []
    assert client.get("/api/learn/items").json() == []
    assert client.get("/api/reading/plans").json() == []
    assert client.get("/api/reading/logs").json() == []
    assert client.get("/api/profile/photo").status_code == 404
    assert client.get("/api/profile").json()["bio"] == ""
    again = client.get("/api/export").json()
    assert again["notes"] == [] and again["learn_reviews"] == [] and again["profile_photo"] is None
