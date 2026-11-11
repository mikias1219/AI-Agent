"""Google list clients: Important Gmail ≤100 and upcoming Calendar."""

from __future__ import annotations

from datetime import UTC, datetime
from urllib.parse import parse_qs, urlparse

import httpx

from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient


def test_list_gmail_requests_important_and_caps_window():
    seen: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/messages"):
            seen["list"] = str(request.url)
            qs = parse_qs(urlparse(str(request.url)).query)
            assert "is:important" in (qs.get("q") or [""])[0]
            assert int((qs.get("maxResults") or ["0"])[0]) <= 100
            return httpx.Response(200, json={"messages": [{"id": "m1"}, {"id": "m2"}]})
        return httpx.Response(
            200,
            json={
                "id": "m1",
                "snippet": "hi",
                "internalDate": "1700000000000",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "a@b.com"},
                        {"name": "Subject", "value": "S"},
                    ]
                },
            },
        )

    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    out = client.list_gmail(page=1, page_size=8)
    assert "list" in seen
    assert out["total"] == 2
    assert out["items"][0]["subject"] == "S"


def test_list_calendar_uses_time_min_now_not_epoch():
    def handler(request: httpx.Request) -> httpx.Response:
        qs = parse_qs(urlparse(str(request.url)).query)
        time_min = (qs.get("timeMin") or [""])[0]
        assert time_min != "1970-01-01T00:00:00Z"
        parsed = datetime.fromisoformat(time_min.replace("Z", "+00:00"))
        assert abs((datetime.now(UTC) - parsed).total_seconds()) < 86400
        assert (qs.get("orderBy") or [""])[0] == "startTime"
        assert int((qs.get("maxResults") or ["0"])[0]) <= 100
        return httpx.Response(
            200,
            json={
                "items": [
                    {
                        "id": "e1",
                        "summary": "Soon",
                        "start": {"dateTime": "2026-12-01T10:00:00Z"},
                        "location": "",
                    }
                ]
            },
        )

    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    out = client.list_calendar(page=1, page_size=8)
    assert out["total"] == 1
    assert out["items"][0]["title"] == "Soon"


def test_list_gmail_paginates_within_window():
    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        if path.endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": f"m{i}"} for i in range(20)]})
        mid = path.rstrip("/").split("/")[-1]
        return httpx.Response(
            200,
            json={
                "id": mid,
                "snippet": "",
                "internalDate": "1700000000000",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "a@b.com"},
                        {"name": "Subject", "value": mid},
                    ]
                },
            },
        )

    client = GoogleApiClient(
        access_token_provider=lambda: "tok",
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    page2 = client.list_gmail(page=2, page_size=8)
    assert page2["total"] == 20
    assert len(page2["items"]) == 8
    assert page2["items"][0]["id"] == "m8"
