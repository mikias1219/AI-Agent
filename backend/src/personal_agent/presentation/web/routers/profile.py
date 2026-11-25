"""Profile photo and notification preferences (docs/LIFE_API_CONTRACT.md section 5)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Request, Response

from personal_agent.app.container import AppContainer
from personal_agent.domain.life import LifeNotFound
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER

PHOTO_URL = "/api/profile/photo"


def build_profile_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["profile"])

    @router.put(PHOTO_URL)
    def put_photo(body: Annotated[dict[str, Any], Body()]) -> dict[str, str]:
        container.photos.put(DASHBOARD_OWNER, body)
        return {"photo_url": PHOTO_URL}

    @router.get(PHOTO_URL)
    def get_photo(request: Request) -> Response:
        photo = container.photos.get(DASHBOARD_OWNER)
        if photo is None:
            raise LifeNotFound("No profile photo.")
        etag = f'"{photo.etag}"'
        headers = {
            "ETag": etag,
            "Cache-Control": "private, max-age=0, must-revalidate",
            "X-Content-Type-Options": "nosniff",
        }
        if request.headers.get("if-none-match") == etag:
            return Response(status_code=304, headers=headers)
        return Response(content=photo.content, media_type=photo.mime, headers=headers)

    @router.delete(PHOTO_URL, status_code=204)
    def delete_photo() -> Response:
        container.photos.delete(DASHBOARD_OWNER)
        return Response(status_code=204)

    @router.get("/api/profile/notifications")
    def get_notifications() -> dict[str, Any]:
        return container.notifications.get(DASHBOARD_OWNER)

    @router.patch("/api/profile/notifications")
    def patch_notifications(body: Annotated[dict[str, Any], Body()]) -> dict[str, Any]:
        return container.notifications.update(DASHBOARD_OWNER, body)

    return router
