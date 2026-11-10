import base64
import json
import httpx
import pytest
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient, GoogleApiError


def test_send_gmail_posts_raw_message():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content.decode())
        return httpx.Response(200, json={"id": "m1", "labelIds": ["SENT"]})

    transport = httpx.MockTransport(handler)
    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=transport),
    )
    result = client.send_gmail(to="a@b.com", subject="Hi", body="Hello")
    assert result["id"] == "m1"
    assert "gmail.googleapis.com" in seen["url"] and seen["url"].endswith("/messages/send")
    raw = base64.urlsafe_b64decode(seen["body"]["raw"] + "==")
    assert b"To: a@b.com" in raw
    assert b"Subject: Hi" in raw


def test_create_calendar_event_posts_primary():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert "calendars/primary/events" in str(request.url)
        return httpx.Response(200, json={"id": "e1", "summary": "Sync"})

    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    out = client.create_calendar_event(
        title="Sync",
        starts_at="2026-11-11T10:00:00Z",
        ends_at="2026-11-11T11:00:00Z",
        location="",
    )
    assert out["id"] == "e1"
