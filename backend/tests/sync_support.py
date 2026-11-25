"""Shared offline helpers for the days, Drive and Calendar tests (no network, ever)."""

from __future__ import annotations

import base64
import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi.testclient import TestClient

from personal_agent.app.container import AppContainer, build_app
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app

OWNER = "dashboard"
PASSWORD = "correct horse battery staple"
SALT = b"sync-test-salt"
ALL_SCOPES = (
    "openid email https://www.googleapis.com/auth/drive.file "
    "https://www.googleapis.com/auth/calendar.events "
    "https://www.googleapis.com/auth/gmail.modify"
)
NO_DRIVE_SCOPES = "openid email https://www.googleapis.com/auth/calendar.events"


class Clock:
    """Controlled clock: tests move time explicitly."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now = self.now + timedelta(**kwargs)


class FakeGoogle:
    """In-memory Drive and Calendar behind httpx.MockTransport. Records every request."""

    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.folders: dict[tuple[str, str], str] = {}  # (name, parent) -> id
        self.files: dict[str, dict[str, Any]] = {}  # id -> {name, parents, content, mime}
        self.events: dict[str, dict[str, Any]] = {}
        self.counter = 0
        self.fail_status: dict[str, int] = {}  # "upload" | "calendar" -> status
        self.missing_files: set[str] = set()  # Drive ids that now answer 404

    # -- helpers -------------------------------------------------------------------

    def _next(self, prefix: str) -> str:
        self.counter += 1
        return f"{prefix}{self.counter}"

    def calls(self, method: str | None = None, contains: str = "") -> list[httpx.Request]:
        return [
            r
            for r in self.requests
            if (method is None or r.method == method) and contains in str(r.url)
        ]

    def uploads(self) -> list[httpx.Request]:
        return [r for r in self.requests if "/upload/drive/v3/files" in str(r.url)]

    @property
    def deletes(self) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == "DELETE"]

    def client(self, *, read_only: bool = False) -> GoogleApiClient:
        return GoogleApiClient(
            access_token_provider=lambda: "test-token",
            http_client=httpx.Client(transport=httpx.MockTransport(self.handle)),
            read_only_provider=lambda: read_only,
        )

    # -- the transport ---------------------------------------------------------------

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = urlsplit(str(request.url))
        query = parse_qs(url.query)
        path = url.path
        if path.startswith("/upload/drive/v3/files"):
            return self._upload(request, path, query)
        if path == "/drive/v3/files" and request.method == "GET":
            q = query.get("q", [""])[0]
            name = re.search(r"name = '((?:[^'\\]|\\.)*)'", q)
            parent = re.search(r"'([^']+)' in parents", q)
            key = (name.group(1) if name else "", parent.group(1) if parent else "")
            found = self.folders.get(key)
            files = (
                [{"id": found, "webViewLink": f"https://drive.example/folders/{found}"}]
                if found
                else []
            )
            return httpx.Response(200, json={"files": files})
        if path == "/drive/v3/files" and request.method == "POST":
            body = json.loads(request.content)
            folder_id = self._next("fld")
            self.folders[(body["name"], body["parents"][0])] = folder_id
            return httpx.Response(
                200,
                json={"id": folder_id, "webViewLink": f"https://drive.example/folders/{folder_id}"},
            )
        if path.startswith("/calendar/v3/calendars/primary/events"):
            return self._calendar(request, path)
        return httpx.Response(404, json={"error": "unexpected"})

    def _upload(
        self, request: httpx.Request, path: str, query: dict[str, list[str]]
    ) -> httpx.Response:
        if "upload" in self.fail_status:
            return httpx.Response(self.fail_status["upload"], json={"error": "denied"})
        content_type = request.headers.get("content-type", "")
        boundary = content_type.split("boundary=")[1]
        parts = request.content.split(f"--{boundary}".encode())
        meta_part, media_part = parts[1], parts[2]
        metadata = json.loads(meta_part.split(b"\r\n\r\n", 1)[1].rsplit(b"\r\n", 1)[0])
        media_head, media = media_part.split(b"\r\n\r\n", 1)
        media = media.rsplit(b"\r\n", 1)[0]
        mime = re.search(rb"Content-Type: ([^\r\n]+)", media_head).group(1).decode()  # type: ignore[union-attr]
        target = path.rsplit("/", 1)[1] if path != "/upload/drive/v3/files" else ""
        if request.method == "PATCH":
            if target in self.missing_files or target not in self.files:
                return httpx.Response(404, json={"error": "gone"})
            self.files[target]["name"] = metadata["name"]
            self.files[target]["content"] = media
            self.files[target]["mime"] = mime
            file_id = target
        else:
            file_id = self._next("file")
            self.files[file_id] = {
                "name": metadata["name"],
                "parents": metadata.get("parents", []),
                "content": media,
                "mime": mime,
            }
        return httpx.Response(
            200, json={"id": file_id, "webViewLink": f"https://drive.example/file/{file_id}"}
        )

    def _calendar(self, request: httpx.Request, path: str) -> httpx.Response:
        if "calendar" in self.fail_status:
            return httpx.Response(self.fail_status["calendar"], json={"error": "denied"})
        body = json.loads(request.content) if request.content else {}
        if request.method == "POST":
            event_id = self._next("evt")
            self.events[event_id] = body
            return httpx.Response(200, json={"id": event_id})
        event_id = path.rsplit("/", 1)[1]
        if request.method == "PATCH":
            if event_id not in self.events:
                return httpx.Response(404, json={"error": "gone"})
            self.events[event_id].update(body)
            return httpx.Response(200, json={"id": event_id})
        if request.method == "GET":
            return httpx.Response(200, json={"items": []})
        return httpx.Response(405)


def hash_password(password: str) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), SALT, 310_000)
    salt = base64.urlsafe_b64encode(SALT).decode().rstrip("=")
    return f"{salt}${base64.urlsafe_b64encode(digest).decode().rstrip('=')}"


def build_sync_app(
    tmp_path: Any,
    clock: Clock,
    *,
    google: FakeGoogle | None = None,
    scopes: str | None = ALL_SCOPES,
    read_only: bool = False,
    timezone: str | None = None,
) -> tuple[AppContainer, FakeGoogle]:
    """A real app on a temp SQLite DB. Google is connected (or not) and fully mocked."""
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'sync.db'}",
            "DASHBOARD_PASSWORD_HASH": hash_password(PASSWORD),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
            "GOOGLE_CLIENT_ID": "cid",
            "GOOGLE_CLIENT_SECRET": "csecret",
        }
    )
    container = build_app(settings=settings, provider=FakeProvider(), clock=clock)
    fake = google or FakeGoogle()
    api = fake.client()
    container.drive_sync._client = api  # noqa: SLF001
    container.calendar_sync._client = api  # noqa: SLF001
    container.days._events = lambda tmin, tmax: api.list_calendar_range(  # noqa: SLF001
        time_min=tmin, time_max=tmax
    )["items"]
    if scopes is not None:
        container.google.save_tokens(
            email="owner@example.test",
            access_token="a",
            refresh_token="r",
            scopes=scopes,
            read_only=read_only,
        )
    if timezone:
        container.profiles.update(OWNER, timezone=timezone)
    return container, fake


def dashboard_client(container: AppContainer, tmp_path: Any, monkeypatch: Any) -> TestClient:
    monkeypatch.chdir(tmp_path)  # login lockout file lives under ./data
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    app = create_dashboard_app(container=container, frontend_dir=frontend)
    client = TestClient(app, base_url="http://127.0.0.1")
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client


def utc(year: int, month: int, day: int, hour: int = 12, minute: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=UTC)
