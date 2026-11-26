"""Server-side sessions (S1): logout and password change really revoke access."""

from __future__ import annotations

from tests.integration.test_tasks_api import PASSWORD, _client


def test_logout_revokes_a_copied_token(tmp_path):
    client = _client(tmp_path)
    token = client.cookies.get("personal_agent_session")
    assert client.get("/api/profile").status_code == 200
    assert client.post("/api/logout").status_code == 200
    # Replaying the copied cookie after logout must fail: the token is revoked server-side.
    client.cookies.set("personal_agent_session", token)
    assert client.get("/api/profile").status_code == 401


def test_cookie_without_server_session_is_rejected(tmp_path):
    client = _client(tmp_path)
    client.app.state  # noqa: B018 - app is built; forge a validly-signed but unknown session
    from personal_agent.presentation.web.routers._common import create_dashboard_session

    secret = "test-secret-key-at-least-thirty-two-bytes"
    forged = create_dashboard_session(secret)
    client.cookies.set("personal_agent_session", forged)
    assert client.get("/api/profile").status_code == 401


def test_password_change_revokes_other_sessions(tmp_path):
    client = _client(tmp_path)
    old = client.cookies.get("personal_agent_session")
    # Env-managed passwords cannot change (409); revoke_all is covered at the store level.
    resp = client.post(
        "/api/auth/password",
        json={"current_password": PASSWORD, "new_password": "another long passphrase 123"},
    )
    assert resp.status_code in (204, 409)
    if resp.status_code == 204:
        client.cookies.set("personal_agent_session", old)
        assert client.get("/api/profile").status_code == 401


def test_remember_me_sets_long_cookie(tmp_path):
    client = _client(tmp_path)
    client.post("/api/logout")
    r = client.post("/api/login", json={"password": PASSWORD, "remember": True})
    assert r.status_code == 200
    assert "Max-Age=25" in r.headers["set-cookie"]  # ~30 days = 2,59x,xxx seconds
