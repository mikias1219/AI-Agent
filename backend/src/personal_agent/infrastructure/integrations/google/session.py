"""Session-scoped Google access token provider (domain errors, not HTTP)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class GoogleNotConnectedError(RuntimeError):
    pass


def make_access_token_provider(*, store: Any, settings: Any) -> Callable[[], str]:
    """Return a callable that loads/refreshes the Google access token for API calls."""

    def provider() -> str:
        from personal_agent.infrastructure.integrations.google.oauth import (
            GOOGLE_SCOPES,
            GoogleOAuthClient,
            GoogleOAuthError,
        )

        tokens = store.load_tokens()
        access = tokens.get("access_token") or ""
        refresh = tokens.get("refresh_token") or ""
        if not access and not refresh:
            raise GoogleNotConnectedError(
                "Google is not connected. Connect Google under Connections."
            )
        oauth_configured = bool(settings.google_client_id and settings.google_client_secret)
        if refresh and oauth_configured:
            oauth = GoogleOAuthClient(
                client_id=settings.google_client_id,
                client_secret=settings.google_client_secret,
                redirect_uri=settings.google_redirect_uri,
            )
            try:
                refreshed = oauth.refresh(refresh)
                access = refreshed["access_token"]
                store.save_tokens(
                    email=tokens.get("email") or "",
                    access_token=access,
                    refresh_token=refresh,
                    scopes=tokens.get("scopes") or " ".join(GOOGLE_SCOPES),
                )
            except GoogleOAuthError:
                if not access:
                    raise GoogleNotConnectedError(
                        "Google token refresh failed. Reconnect Google."
                    ) from None
        if not access:
            raise GoogleNotConnectedError("Google access token missing. Reconnect Google.")
        return access

    return provider
