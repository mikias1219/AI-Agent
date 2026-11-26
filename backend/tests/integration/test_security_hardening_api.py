"""API-level checks for the Phase 0 hardening (ADR-0025).

- Google OAuth callback accepts only a state minted for a logged-in owner, once.
- The tick endpoint does not reuse the session signing key in production.
- MCP transport rules are enforced on the routes, and tool refresh works twice.
"""

from __future__ import annotations

import base64
import hashlib
from urllib.parse import parse_qs, urlsplit

import pytest
from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.integrations.google.oauth import GoogleOAuthClient
from personal_agent.infrastructure.integrations.mcp.client import FakeMcpClient
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app

PASSWORD = "correct horse battery staple"
SALT = b"hardening-api-test-salt"
SECRET_KEY = "test-secret-key-at-least-thirty-two-bytes"
PROD_ORIGIN = "https://compass.example"


def _password_hash() -> str:
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    return f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"


def _client(tmp_path, *, production: bool = False, **env: str) -> TestClient:
    values = {
        "PERSONAL_AGENT_PROVIDER": "fake",
        "DATABASE_URL": f"sqlite:///{tmp_path / 'hardening.db'}",
        "DEMO_DATABASE_URL": f"sqlite:///{tmp_path / 'hardening-demo.db'}",
        "DASHBOARD_PASSWORD_HASH": _password_hash(),
        "DASHBOARD_SECRET_KEY": SECRET_KEY,
        **env,
    }
    if production:
        values |= {"ENVIRONMENT": "production", "FRONTEND_ORIGIN": PROD_ORIGIN}
    settings = Settings.from_env(values)
    frontend = tmp_path / "frontend"
    frontend.mkdir(exist_ok=True)
    (frontend / "index.html").write_text('<div id="root"></div>')
    app = create_dashboard_app(
        container=build_app(settings=settings, provider=FakeProvider()),
        frontend_dir=frontend,
    )
    return TestClient(app, base_url=PROD_ORIGIN if production else "http://127.0.0.1")


def _login(client: TestClient) -> None:
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200


# -- Google OAuth state ------------------------------------------------------------------------


@pytest.fixture
def google_client(tmp_path, monkeypatch) -> TestClient:
    exchanged: list[str] = []

    def exchange_code(_self, code: str) -> dict[str, str]:
        exchanged.append(code)
        return {"access_token": f"access-{code}", "refresh_token": f"refresh-{code}"}

    monkeypatch.setattr(GoogleOAuthClient, "exchange_code", exchange_code)
    monkeypatch.setattr(
        GoogleOAuthClient, "userinfo", lambda _self, _token: {"email": "owner@example.com"}
    )
    client = _client(
        tmp_path,
        GOOGLE_CLIENT_ID="client-id.apps.googleusercontent.com",
        GOOGLE_CLIENT_SECRET="client-secret",
    )
    client.exchanged = exchanged  # type: ignore[attr-defined]
    return client


def _state_from_connect(client: TestClient, *, read_only: bool = True) -> str:
    response = client.post(f"/api/google/connect?read_only={'true' if read_only else 'false'}")
    assert response.status_code == 200
    query = parse_qs(urlsplit(response.json()["auth_url"]).query)
    return query["state"][0]


@pytest.mark.parametrize("state", ["", "ro=0", "ro=1", "v1.0.9999999999.nonce.forged"])
def test_callback_rejects_states_the_server_did_not_sign(google_client, state):
    _login(google_client)
    anonymous = TestClient(google_client.app, base_url="http://127.0.0.1")
    response = anonymous.get("/api/google/callback", params={"code": "attacker", "state": state})
    assert response.status_code == 400
    assert google_client.exchanged == []  # type: ignore[attr-defined]
    assert google_client.get("/api/google/status").json()["connected"] is False


def test_callback_accepts_owner_state_once_and_keeps_read_only_choice(google_client):
    _login(google_client)
    state = _state_from_connect(google_client, read_only=False)
    # Google redirects the browser to the API host, where the session cookie is absent.
    anonymous = TestClient(google_client.app, base_url="http://127.0.0.1")
    first = anonymous.get("/api/google/callback", params={"code": "good", "state": state})
    assert first.status_code == 200
    status = google_client.get("/api/google/status").json()
    assert status["connected"] is True
    assert status["read_only"] is False

    replay = anonymous.get("/api/google/callback", params={"code": "again", "state": state})
    assert replay.status_code == 400
    assert google_client.exchanged == ["good"]  # type: ignore[attr-defined]


def test_connect_requires_login(google_client):
    assert google_client.post("/api/google/connect").status_code == 401


# -- Tick secret -------------------------------------------------------------------------------


def test_local_tick_still_accepts_the_dashboard_key(tmp_path):
    client = _client(tmp_path)
    response = client.post("/internal/tick", headers={"X-Compass-Tick-Secret": SECRET_KEY})
    assert response.status_code == 200


def test_production_tick_never_accepts_the_session_signing_key(tmp_path):
    client = _client(tmp_path, production=True)
    response = client.post("/internal/tick", headers={"X-Compass-Tick-Secret": SECRET_KEY})
    assert response.status_code == 401


def test_production_tick_accepts_only_its_own_secret(tmp_path):
    client = _client(tmp_path, production=True, INTERNAL_TICK_SECRET="tick-only-secret")
    ok = client.post("/internal/tick", headers={"X-Compass-Tick-Secret": "tick-only-secret"})
    assert ok.status_code == 200
    reused = client.post("/internal/tick", headers={"X-Compass-Tick-Secret": SECRET_KEY})
    assert reused.status_code == 401


# -- MCP routes --------------------------------------------------------------------------------


def _use_fake_mcp(client: TestClient) -> None:
    client.app.state.container.mcp_adapter._client_factory = lambda **_kwargs: FakeMcpClient()


def test_adding_a_second_mcp_server_refreshes_tools_without_error(tmp_path):
    client = _client(tmp_path)
    _login(client)
    _use_fake_mcp(client)
    for name in ("One", "Two"):
        response = client.post(
            "/api/mcp/servers",
            json={"name": name, "transport": "http", "url": "http://127.0.0.1:9000/mcp"},
        )
        assert response.status_code == 201, response.text
    assert response.json()["registered_tools"] == 2
    servers = client.get("/api/mcp/servers").json()
    assert [row["blocked_reason"] for row in servers] == [None, None]


def test_production_refuses_stdio_and_private_url_servers(tmp_path):
    client = _client(tmp_path, production=True)
    _login(client)
    _use_fake_mcp(client)
    stdio = client.post(
        "/api/mcp/servers", json={"name": "Shell", "transport": "stdio", "command": "id"}
    )
    assert stdio.status_code == 400
    assert "stdio" in stdio.json()["detail"]
    private = client.post(
        "/api/mcp/servers",
        json={"name": "Meta", "transport": "http", "url": "http://169.254.169.254/"},
    )
    assert private.status_code == 400
    assert client.get("/api/mcp/servers").json() == []

    public = client.post(
        "/api/mcp/servers",
        json={"name": "Notes", "transport": "http", "url": "https://mcp.example.com/mcp"},
    )
    assert public.status_code == 201, public.text


def test_production_allows_stdio_when_explicitly_enabled(tmp_path):
    client = _client(tmp_path, production=True, MCP_ALLOW_STDIO="1")
    _login(client)
    _use_fake_mcp(client)
    response = client.post(
        "/api/mcp/servers", json={"name": "Local", "transport": "stdio", "command": "server"}
    )
    assert response.status_code == 201, response.text
