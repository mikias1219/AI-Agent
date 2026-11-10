"""Google OAuth token exchange, refresh, revoke, and userinfo."""

from __future__ import annotations

from typing import Any

import httpx

TOKEN_URL = "https://oauth2.googleapis.com/token"
REVOKE_URL = "https://oauth2.googleapis.com/revoke"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"

GOOGLE_SCOPES = [
    "openid",
    "email",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/drive.readonly",
]


class GoogleOAuthError(RuntimeError):
    pass


class GoogleOAuthClient:
    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._http = http_client

    def _client(self) -> httpx.Client:
        return self._http or httpx.Client(timeout=30.0)

    def exchange_code(self, code: str) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.post(
                TOKEN_URL,
                data={
                    "code": code,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "redirect_uri": self._redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            if response.status_code >= 400:
                raise GoogleOAuthError(f"Token exchange failed ({response.status_code}).")
            data = response.json()
            if not data.get("access_token"):
                raise GoogleOAuthError("Token exchange returned no access_token.")
            return data
        finally:
            if owns:
                client.close()

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.post(
                TOKEN_URL,
                data={
                    "refresh_token": refresh_token,
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                    "grant_type": "refresh_token",
                },
            )
            if response.status_code >= 400:
                raise GoogleOAuthError(f"Token refresh failed ({response.status_code}).")
            data = response.json()
            if not data.get("access_token"):
                raise GoogleOAuthError("Token refresh returned no access_token.")
            return data
        finally:
            if owns:
                client.close()

    def revoke(self, token: str) -> None:
        if not token:
            return
        client = self._client()
        owns = self._http is None
        try:
            client.post(REVOKE_URL, params={"token": token})
        finally:
            if owns:
                client.close()

    def userinfo(self, access_token: str) -> dict[str, Any]:
        client = self._client()
        owns = self._http is None
        try:
            response = client.get(
                USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code >= 400:
                raise GoogleOAuthError(f"Userinfo failed ({response.status_code}).")
            return response.json()
        finally:
            if owns:
                client.close()
