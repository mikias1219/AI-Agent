"""Google OAuth and list endpoints (Phase 6 split)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Any
from urllib.parse import urlencode

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response
from pydantic import BaseModel

from personal_agent.app.container import AppContainer
from personal_agent.application.security.oauth_state import (
    OAuthStateError,
    issue_state,
    verify_state,
)


class GoogleSettingsPatchRequest(BaseModel):
    read_only: bool


def build_google_router(
    container: AppContainer,
    *,
    session_key: Callable[[], str],
) -> APIRouter:
    router = APIRouter(tags=["google"])

    def google_oauth_configured() -> bool:
        return bool(container.settings.google_client_id and container.settings.google_client_secret)

    def google_oauth(*, read_only: bool = True) -> Any:
        from personal_agent.infrastructure.integrations.google.oauth import (
            GoogleOAuthClient,
            scopes_for_read_only,
        )

        return GoogleOAuthClient(
            client_id=container.settings.google_client_id,
            client_secret=container.settings.google_client_secret,
            redirect_uri=container.settings.google_redirect_uri,
        ), scopes_for_read_only(read_only)

    from personal_agent.infrastructure.integrations.google.session import (
        GoogleNotConnectedError,
        make_access_token_provider,
    )

    google_token_provider = make_access_token_provider(
        store=container.google, settings=container.settings
    )

    def google_access_token() -> str:
        try:
            return google_token_provider()
        except GoogleNotConnectedError as exc:
            message = str(exc)
            if "Connect Google under Connections" in message:
                message = "Google is not connected. Connect from Connections first."
            raise HTTPException(400, message) from None

    def google_auth_url(*, read_only: bool) -> str:
        scopes = google_oauth(read_only=read_only)[1]
        params = urlencode(
            {
                "client_id": container.settings.google_client_id,
                "redirect_uri": container.settings.google_redirect_uri,
                "response_type": "code",
                "scope": " ".join(scopes),
                "access_type": "offline",
                "prompt": "consent",
                "state": issue_state(session_key(), read_only=read_only),
            }
        )
        return f"https://accounts.google.com/o/oauth2/v2/auth?{params}"

    @router.get("/api/google/status")
    def google_status() -> dict[str, Any]:
        return container.google.status(oauth_configured=google_oauth_configured())

    @router.post("/api/google/connect")
    def google_connect(
        read_only: Annotated[bool, Query()] = True,
    ) -> dict[str, Any]:
        if not google_oauth_configured():
            raise HTTPException(
                400,
                "Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env "
                "(free Google Cloud OAuth client), then restart.",
            )
        auth_url = google_auth_url(read_only=read_only)
        container.google.set_read_only(read_only)
        container.audit.record("google.connect_started", "dashboard", {"read_only": read_only})
        return {"auth_url": auth_url, "local_dev_connected": False, "read_only": read_only}

    @router.patch("/api/google/settings")
    def google_settings_patch(request: GoogleSettingsPatchRequest) -> dict[str, Any]:
        if not google_oauth_configured():
            raise HTTPException(400, "Google OAuth is not configured.")
        status = container.google.status(oauth_configured=True)
        if not status.get("connected"):
            raise HTTPException(400, "Connect Google before changing settings.")
        wants_write = not request.read_only
        currently_ro = bool(status.get("read_only", True))
        container.google.set_read_only(request.read_only)
        auth_url = None
        if wants_write and currently_ro:
            auth_url = google_auth_url(read_only=False)
        container.audit.record(
            "google.settings_patched",
            "dashboard",
            {"read_only": request.read_only, "reconsent": bool(auth_url)},
        )
        next_status = container.google.status(oauth_configured=True)
        if auth_url:
            next_status["auth_url"] = auth_url
        return next_status

    @router.get("/api/google/callback")
    def google_callback(
        request: Request,
        code: str = Query(default=""),
        error: str = Query(default=""),
        state: str = Query(default=""),
    ):
        from personal_agent.infrastructure.integrations.google.oauth import GoogleOAuthError

        if error:
            raise HTTPException(400, f"Google OAuth error: {error}")
        if not code:
            raise HTTPException(400, "Missing OAuth code.")
        if not google_oauth_configured():
            raise HTTPException(400, "Google OAuth is not configured.")
        try:
            verified = verify_state(session_key(), state)
            request.app.state.google_oauth_states.claim(verified)
        except OAuthStateError:
            container.audit.record("google.oauth_state_rejected", "dashboard", {})
            raise HTTPException(
                400,
                "This Google sign-in link is not valid or has expired. "
                "Start again from Connections.",
            ) from None
        read_only = verified.read_only
        oauth, scopes = google_oauth(read_only=read_only)
        try:
            token_payload = oauth.exchange_code(code)
            access = token_payload["access_token"]
            refresh = token_payload.get("refresh_token") or ""
            info = oauth.userinfo(access)
            email = str(info.get("email") or "google-oauth-user")
            if not refresh:
                existing = container.google.load_tokens()
                refresh = existing.get("refresh_token") or ""
            container.google.save_tokens(
                email=email,
                access_token=access,
                refresh_token=refresh,
                scopes=token_payload.get("scope") or " ".join(scopes),
                read_only=read_only,
            )
        except GoogleOAuthError as exc:
            raise HTTPException(400, str(exc)) from exc
        container.audit.record(
            "google.oauth_callback",
            "dashboard",
            {"email": email, "read_only": read_only},
        )
        return Response(
            content=(
                "<html><body style='font-family:sans-serif;padding:2rem'>"
                "<h1>Google connected</h1>"
                "<p>You can close this tab and return to AURA.</p>"
                "</body></html>"
            ),
            media_type="text/html",
        )

    @router.post("/api/google/disconnect")
    def google_disconnect() -> dict[str, bool]:
        tokens = container.google.clear_tokens()
        if google_oauth_configured():
            oauth, _scopes = google_oauth()
            oauth.revoke(tokens.get("refresh_token") or tokens.get("access_token") or "")
        container.audit.record("google.disconnected", "dashboard", {})
        return {"disconnected": True}

    @router.get("/api/google/gmail")
    def google_gmail(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=google_access_token)
        try:
            return client.list_gmail(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    @router.get("/api/google/calendar")
    def google_calendar(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=google_access_token)
        try:
            return client.list_calendar(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    @router.get("/api/google/drive")
    def google_drive(
        page: int = Query(default=1, ge=1),
        page_size: int = Query(default=8, ge=1, le=50),
    ) -> dict[str, Any]:
        from personal_agent.infrastructure.integrations.google.clients import (
            GoogleApiClient,
            GoogleApiError,
        )

        client = GoogleApiClient(access_token_provider=google_access_token)
        try:
            return client.list_drive(page=page, page_size=page_size)
        except GoogleApiError as exc:
            raise HTTPException(502, str(exc)) from exc

    return router