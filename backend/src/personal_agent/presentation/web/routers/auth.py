"""Login, registration, profile and onboarding (Phase 6 split)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.security.login_lockout import LoginLockoutStore
from personal_agent.application.services.task_service import UNSET
from personal_agent.domain.exceptions import StorageError
from personal_agent.presentation.web.routers._common import (
    DASHBOARD_OWNER,
    create_dashboard_session,
    profile_payload,
    valid_dashboard_session,
)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=1024)
    email: str = Field(default="", max_length=254)


class RegistrationRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: str = Field(max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    password: str = Field(min_length=8, max_length=1024)


class ProfilePatchRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)
    language: str | None = Field(default=None, min_length=1, max_length=16)


class WizardCompleteRequest(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    timezone: str | None = Field(default=None, min_length=1, max_length=64)


def build_auth_router(
    container: AppContainer,
    *,
    session_key: Callable[[], str],
    cookie_secure: bool,
    cookie_samesite: str,
) -> APIRouter:
    router = APIRouter(tags=["auth"])

    @router.get("/api/auth")
    def auth_status(request: Request) -> dict[str, Any]:
        authenticated = valid_dashboard_session(request, session_key())
        return {
            "authenticated": authenticated,
            "registered": container.auth.registered(),
            "user": container.auth.profile() if authenticated else None,
            "email_required": container.auth.requires_email(),
        }

    @router.post("/api/login")
    def login(request: Request, credentials: LoginRequest):
        remote_addr = request.client.host if request.client else "unknown"
        lockout: LoginLockoutStore = request.app.state.login_lockout
        if lockout.is_locked(remote_addr):
            raise HTTPException(status_code=429, detail="Too many attempts. Try again shortly.")
        if not container.auth.verify(credentials.password, credentials.email):
            lockout.record_failure(remote_addr)
            raise HTTPException(status_code=401, detail="Incorrect password.")
        lockout.clear(remote_addr)
        response = JSONResponse({"authenticated": True, "user": container.auth.profile()})
        response.set_cookie(
            "personal_agent_session",
            create_dashboard_session(session_key()),
            max_age=12 * 60 * 60,
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
            path="/",
        )
        return response

    @router.post("/api/register", status_code=201)
    def register(credentials: RegistrationRequest):
        try:
            container.auth.register(credentials.name, credentials.email, credentials.password)
        except StorageError as exc:
            raise HTTPException(409, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        container.audit.record("workspace.registered", "dashboard", {})
        return {"registered": True}

    @router.post("/api/logout")
    def logout():
        response = JSONResponse({"authenticated": False})
        response.delete_cookie(
            "personal_agent_session",
            path="/",
            httponly=True,
            secure=cookie_secure,
            samesite=cookie_samesite,
        )
        return response

    @router.get("/api/profile")
    def get_profile() -> dict[str, Any]:
        return profile_payload(container.profiles.get(DASHBOARD_OWNER))

    @router.patch("/api/profile")
    def patch_profile(request: ProfilePatchRequest) -> dict[str, Any]:
        sent = request.model_fields_set
        try:
            profile = container.profiles.update(
                DASHBOARD_OWNER,
                name=request.name if "name" in sent else UNSET,
                timezone=request.timezone if request.timezone is not None else UNSET,
                language=request.language if request.language is not None else UNSET,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return profile_payload(profile)

    @router.get("/api/onboarding")
    def get_onboarding() -> dict[str, Any]:
        return container.onboarding.payload(DASHBOARD_OWNER)

    @router.post("/api/onboarding/wizard")
    def complete_wizard(request: WizardCompleteRequest) -> dict[str, Any]:
        try:
            return container.onboarding.complete_wizard(
                DASHBOARD_OWNER, name=request.name, timezone=request.timezone
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.post("/api/onboarding/skip-briefing")
    def skip_briefing() -> dict[str, Any]:
        return container.onboarding.skip_briefing(DASHBOARD_OWNER)

    return router