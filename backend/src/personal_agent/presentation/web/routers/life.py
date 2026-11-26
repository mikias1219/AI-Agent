"""Notes, diary, files, learning and reading (docs/LIFE_API_CONTRACT.md sections 1-4).

Bodies are read as plain JSON objects and validated in `domain/life.py`, so every invalid
input is a 400 with `{"detail": ...}` as the contract says (not FastAPI's 422).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Annotated, Any
from urllib.parse import quote

from fastapi import APIRouter, Body, Query, Response

from personal_agent.app.container import AppContainer
from personal_agent.application.life_payloads import (
    file_payload,
    learn_payload,
    note_payload,
    plan_payload,
    reading_log_payload,
)
from personal_agent.domain.life import FileItem, LifeError, Note, is_inline
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER

JsonBody = Annotated[dict[str, Any], Body()]
Limit = Annotated[int | None, Query()]
Offset = Annotated[int | None, Query()]


def content_disposition(name: str, *, inline: bool) -> str:
    if inline:
        return "inline"
    ascii_name = (
        name.encode("ascii", "ignore").decode().replace('"', "").replace("\\", "") or "file"
    )
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(name, safe='')}"


def build_life_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["life"])
    owner = DASHBOARD_OWNER

    def notes_out(notes: Sequence[Note]) -> list[dict[str, Any]]:
        links = container.drive_sync.link_map(owner, ("note", "diary"), [n.id for n in notes])
        return [note_payload(n, links.get(n.id)) for n in notes]

    def files_out(items: Sequence[FileItem]) -> list[dict[str, Any]]:
        links = container.drive_sync.link_map(owner, ("file",), [f.id for f in items])
        return [file_payload(f, links.get(f.id)) for f in items]

    # -- notes and diary -----------------------------------------------------------

    @router.get("/api/notes")
    def list_notes(
        kind: str | None = None,
        q: str = "",
        tag: str = "",
        limit: Limit = None,
        offset: Offset = None,
    ) -> list[dict[str, Any]]:
        found = container.notes.list(owner, kind=kind, q=q, tag=tag, limit=limit, offset=offset)
        return notes_out(found)

    @router.get("/api/notes/stats")
    def note_stats() -> dict[str, Any]:
        return container.notes.stats(owner)

    @router.post("/api/notes", status_code=201)
    def create_note(body: JsonBody) -> dict[str, Any]:
        return notes_out([container.notes.create(owner, body)])[0]

    @router.get("/api/notes/{note_id}")
    def get_note(note_id: str) -> dict[str, Any]:
        return notes_out([container.notes.get(owner, note_id)])[0]

    @router.patch("/api/notes/{note_id}")
    def patch_note(note_id: str, body: JsonBody) -> dict[str, Any]:
        return notes_out([container.notes.update(owner, note_id, body)])[0]

    @router.delete("/api/notes/{note_id}", status_code=204)
    def delete_note(note_id: str) -> Response:
        container.notes.delete(owner, note_id)
        return Response(status_code=204)

    # -- files ---------------------------------------------------------------------

    @router.get("/api/files")
    def list_files(
        kind: str | None = None,
        q: str = "",
        tag: str = "",
        limit: Limit = None,
        offset: Offset = None,
    ) -> list[dict[str, Any]]:
        found = container.files.list(owner, kind=kind, q=q, tag=tag, limit=limit, offset=offset)
        return files_out(found)

    @router.get("/api/files/stats")
    def file_stats() -> dict[str, int]:
        return container.files.stats(owner)

    @router.post("/api/files", status_code=201)
    def upload_file(body: JsonBody) -> dict[str, Any]:
        return files_out([container.files.upload(owner, body)])[0]

    @router.get("/api/files/{file_id}/content")
    def file_content(file_id: str) -> Response:
        item, content = container.files.content(owner, file_id)
        return Response(
            content=content,
            media_type=item.mime,
            headers={
                "X-Content-Type-Options": "nosniff",
                "Content-Disposition": content_disposition(item.name, inline=is_inline(item.mime)),
                "Cache-Control": "private, max-age=0, must-revalidate",
            },
        )

    @router.patch("/api/files/{file_id}")
    def patch_file(file_id: str, body: JsonBody) -> dict[str, Any]:
        return files_out([container.files.update(owner, file_id, body)])[0]

    @router.delete("/api/files/{file_id}", status_code=204)
    def delete_file(file_id: str) -> Response:
        container.files.delete(owner, file_id)
        return Response(status_code=204)

    # -- learning ------------------------------------------------------------------

    @router.get("/api/learn/items")
    def list_learn(
        q: str = "",
        topic: str = "",
        language: str = "",
        due: bool = False,
        limit: Limit = None,
        offset: Offset = None,
    ) -> list[dict[str, Any]]:
        found = container.learn.list(
            owner, q=q, topic=topic, language=language, due=due, limit=limit, offset=offset
        )
        return [learn_payload(i) for i in found]

    @router.post("/api/learn/items", status_code=201)
    def create_learn(body: JsonBody) -> list[dict[str, Any]]:
        if "items" in body:
            raw = body["items"]
            if not isinstance(raw, list) or not all(isinstance(i, Mapping) for i in raw):
                raise LifeError("items must be a list of objects.")
            batch: list[Mapping[str, Any]] = raw
        else:
            batch = [body]
        created, _skipped = container.learn.create_many(owner, batch)
        return [learn_payload(i) for i in created]

    @router.get("/api/learn/stats")
    def learn_stats() -> dict[str, int | None]:
        return container.learn.stats(owner)

    @router.get("/api/learn/topics")
    def learn_topics() -> list[str]:
        return container.learn.topics(owner)

    @router.patch("/api/learn/items/{item_id}")
    def patch_learn(item_id: str, body: JsonBody) -> dict[str, Any]:
        return learn_payload(container.learn.update(owner, item_id, body))

    @router.delete("/api/learn/items/{item_id}", status_code=204)
    def delete_learn(item_id: str) -> Response:
        container.learn.delete(owner, item_id)
        return Response(status_code=204)

    @router.post("/api/learn/items/{item_id}/review")
    def review_learn(item_id: str, body: JsonBody) -> dict[str, Any]:
        return learn_payload(container.learn.review(owner, item_id, str(body.get("result"))))

    # -- reading -------------------------------------------------------------------

    @router.get("/api/reading/templates")
    def reading_templates() -> list[dict[str, Any]]:
        return container.reading.templates()

    @router.get("/api/reading/plans")
    def list_plans(limit: Limit = None, offset: Offset = None) -> list[dict[str, Any]]:
        return [
            plan_payload(p) for p in container.reading.list_plans(owner, limit=limit, offset=offset)
        ]

    @router.post("/api/reading/plans", status_code=201)
    def create_plan(body: JsonBody) -> dict[str, Any]:
        return plan_payload(container.reading.create_plan(owner, body))

    @router.patch("/api/reading/plans/{plan_id}")
    def patch_plan(plan_id: str, body: JsonBody) -> dict[str, Any]:
        return plan_payload(container.reading.update_plan(owner, plan_id, body))

    @router.delete("/api/reading/plans/{plan_id}", status_code=204)
    def delete_plan(plan_id: str) -> Response:
        container.reading.delete_plan(owner, plan_id)
        return Response(status_code=204)

    @router.post("/api/reading/plans/{plan_id}/advance")
    def advance_plan(
        plan_id: str, body: Annotated[dict[str, Any] | None, Body()] = None
    ) -> dict[str, Any]:
        reflection = (body or {}).get("reflection") or ""
        if not isinstance(reflection, str):
            raise LifeError("reflection must be a string.")
        plan, log = container.reading.advance(owner, plan_id, reflection)
        return {"plan": plan_payload(plan), "log": reading_log_payload(log)}

    @router.get("/api/reading/logs")
    def list_logs(
        plan_id: str = "", limit: Limit = None, offset: Offset = None
    ) -> list[dict[str, Any]]:
        found = container.reading.list_logs(owner, plan_id=plan_id, limit=limit, offset=offset)
        return [reading_log_payload(x) for x in found]

    @router.post("/api/reading/logs", status_code=201)
    def create_log(body: JsonBody) -> dict[str, Any]:
        return reading_log_payload(container.reading.create_log(owner, body))

    @router.patch("/api/reading/logs/{log_id}")
    def patch_log(log_id: str, body: JsonBody) -> dict[str, Any]:
        return reading_log_payload(container.reading.update_log(owner, log_id, body))

    @router.delete("/api/reading/logs/{log_id}", status_code=204)
    def delete_log(log_id: str) -> Response:
        container.reading.delete_log(owner, log_id)
        return Response(status_code=204)

    @router.get("/api/reading/stats")
    def reading_stats() -> dict[str, Any]:
        stats = container.reading.stats(owner)
        plan = stats["active_plan"]
        return {**stats, "active_plan": plan_payload(plan) if plan else None}

    return router
