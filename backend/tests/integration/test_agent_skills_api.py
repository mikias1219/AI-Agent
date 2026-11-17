"""GET /api/agent/skills returns the shipped W1–W5 pack."""

from __future__ import annotations

import base64
import hashlib

from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.config.settings import Settings
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.presentation.web.app import create_dashboard_app

PASSWORD = "correct horse battery staple"
SALT = b"skills-api-test-salt"


def test_list_agent_skills(tmp_path) -> None:
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'skills-api.db'}",
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
    body = client.get("/api/agent/skills").json()
    names = {row["name"] for row in body}
    assert names == {
        "daily-briefing",
        "inbox-to-action",
        "plan-my-time",
        "remind-and-follow-up",
        "remember-me",
    }
    remind = next(row for row in body if row["name"] == "remind-and-follow-up")
    assert "reminders" in remind["tool_groups"]
