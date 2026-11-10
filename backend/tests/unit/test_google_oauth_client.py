"""Google OAuth client with mocked HTTP."""

import httpx

from personal_agent.infrastructure.integrations.google.oauth import GoogleOAuthClient


def test_exchange_code_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://oauth2.googleapis.com/token"
        return httpx.Response(200, json={"access_token": "a", "refresh_token": "r"})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    oauth = GoogleOAuthClient(
        client_id="id",
        client_secret="secret",
        redirect_uri="http://127.0.0.1:8000/api/google/callback",
        http_client=client,
    )
    data = oauth.exchange_code("code-1")
    assert data["access_token"] == "a"
    assert data["refresh_token"] == "r"
    client.close()


def test_list_gmail_shapes(monkeypatch):
    from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "messages?" in str(request.url) or str(request.url).endswith("/messages"):
            return httpx.Response(200, json={"messages": [{"id": "m1"}]})
        return httpx.Response(
            200,
            json={
                "id": "m1",
                "snippet": "hi",
                "internalDate": "1700000000000",
                "payload": {
                    "headers": [
                        {"name": "From", "value": "a@b.com"},
                        {"name": "Subject", "value": "Hello"},
                    ]
                },
            },
        )

    transport = httpx.MockTransport(handler)
    http = httpx.Client(transport=transport)
    api = GoogleApiClient(access_token_provider=lambda: "tok", http_client=http)
    result = api.list_gmail(page=1, page_size=8)
    assert result["total"] == 1
    assert result["items"][0]["subject"] == "Hello"
    assert result["items"][0]["from"] == "a@b.com"
    http.close()
