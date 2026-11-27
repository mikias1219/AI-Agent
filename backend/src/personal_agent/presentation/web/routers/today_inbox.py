"""Today, inbox, briefing, activity, approvals and suggestions (Phase 6 split)."""

from __future__ import annotations

import csv
import io
import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.inbox_items import suggestion_payload
from personal_agent.application.security.login_lockout import csv_safe_cell
from personal_agent.domain.approvals import ApprovalStatus
from personal_agent.domain.exceptions import (
    ApprovalConflictError,
    ApprovalForbiddenError,
    StorageError,
    ToolInputError,
)
from personal_agent.domain.suggestions import SUGGESTION_STATUSES, SuggestionError
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER, approval_payload_row


class SuggestionDismissRequest(BaseModel):
    feedback: str = Field(default="", max_length=500)


class ApprovalDecisionRequest(BaseModel):
    approve: bool


class ApprovalEditRequest(BaseModel):
    arguments: dict[str, Any]


def build_today_inbox_router(container: AppContainer) -> APIRouter:
    router = APIRouter(tags=["today", "inbox"])

    def suggestion_error(exc: Exception) -> HTTPException:
        if isinstance(exc, StorageError):
            return HTTPException(status_code=404, detail=str(exc))
        return HTTPException(status_code=409, detail=str(exc))

    def approval_error(exc: Exception) -> HTTPException:
        if isinstance(exc, ApprovalForbiddenError):
            return HTTPException(status_code=403, detail=str(exc))
        if isinstance(exc, ApprovalConflictError):
            return HTTPException(status_code=409, detail=str(exc))
        if isinstance(exc, ToolInputError):
            return HTTPException(status_code=422, detail=str(exc))
        return HTTPException(status_code=404, detail="Approval not found.")

    @router.get("/api/suggestions")
    def list_suggestions(
        status: Annotated[str | None, Query(max_length=16)] = None,
    ) -> list[dict[str, Any]]:
        if status is not None and status not in SUGGESTION_STATUSES:
            raise HTTPException(status_code=400, detail="Unknown suggestion status.")
        now = datetime.now(UTC)
        return [
            suggestion_payload(s, now) for s in container.suggestions.list(DASHBOARD_OWNER, status)
        ]

    @router.post("/api/suggestions/{suggestion_id}/accept")
    def accept_suggestion(suggestion_id: str) -> dict[str, Any]:
        try:
            result = container.suggestions.accept(suggestion_id, DASHBOARD_OWNER)
        except (StorageError, SuggestionError) as exc:
            raise suggestion_error(exc) from exc
        return {
            "id": result.suggestion.id,
            "outcome": result.outcome,
            "summary": result.summary,
            "approval_id": result.suggestion.approval_id,
            "suggestion": suggestion_payload(result.suggestion),
        }

    @router.post("/api/suggestions/{suggestion_id}/dismiss")
    def dismiss_suggestion(
        suggestion_id: str, request: SuggestionDismissRequest | None = None
    ) -> dict[str, Any]:
        try:
            suggestion = container.suggestions.dismiss(
                suggestion_id, DASHBOARD_OWNER, request.feedback if request else ""
            )
        except (StorageError, SuggestionError) as exc:
            raise suggestion_error(exc) from exc
        return {"id": suggestion.id, "suggestion": suggestion_payload(suggestion)}

    @router.get("/api/inbox")
    def inbox(tab: Annotated[str, Query(pattern="^(open|done)$")] = "open") -> dict[str, Any]:
        return container.inbox.build(DASHBOARD_OWNER, tab)

    @router.get("/api/today")
    def today() -> dict[str, Any]:
        return container.today.build(DASHBOARD_OWNER)

    @router.get("/api/nav/counts")
    def nav_counts() -> dict[str, Any]:
        """Sidebar counts: tasks left today and words due. Cheap; polled on navigation."""
        counts: dict[str, Any] = dict(container.today.nav_counts(DASHBOARD_OWNER))
        counts["words_due"] = int(container.learn.stats(DASHBOARD_OWNER)["due"] or 0)
        return counts

    @router.get("/api/score/today")
    def score_today(rest: bool = False) -> dict[str, Any]:
        """Day score 0-100 with the per-area breakdown (rest=true makes the day neutral)."""
        return container.score.for_day(DASHBOARD_OWNER, rest=rest)

    @router.get("/api/score/week")
    def score_week() -> dict[str, Any]:
        return container.score.week(DASHBOARD_OWNER)

    @router.get("/api/calendar/agenda")
    def calendar_agenda(limit: int = Query(default=3, ge=1, le=20)) -> dict[str, Any]:
        return container.agenda.get(limit)

    @router.get("/api/briefing/latest")
    def latest_briefing() -> dict[str, Any]:
        doc = container.scheduler.latest_briefing_document(DASHBOARD_OWNER)
        if doc is None:
            return {"text": None, "sections": [], "sources": {}, "run_id": None}
        payload = doc.to_payload()
        return {
            "text": payload.get("text"),
            "summary": payload.get("summary"),
            "sections": payload.get("sections") or [],
            "sources": payload.get("sources") or {},
            "run_id": payload.get("run_id"),
            "model": payload.get("model"),
            "prompt_version": payload.get("prompt_version"),
        }

    @router.get("/api/activity")
    def activity(
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        origin: Annotated[str | None, Query()] = None,
        event: Annotated[str | None, Query()] = None,
        status: Annotated[str | None, Query()] = None,
    ) -> list[dict[str, Any]]:
        rows = container.audit.list_recent(limit=limit, offset=offset)
        if event:
            rows = [row for row in rows if row.get("event") == event]
        if origin:
            rows = [
                row
                for row in rows
                if isinstance(row.get("details"), dict)
                and str((row.get("details") or {}).get("origin") or "") == origin
            ]
        if status:
            rows = [
                row
                for row in rows
                if isinstance(row.get("details"), dict)
                and str((row.get("details") or {}).get("status") or "") == status
            ]
        return rows

    @router.get("/api/activity/export.csv")
    def activity_export_csv(
        limit: int = Query(default=500, ge=1, le=2000),
    ) -> StreamingResponse:
        rows = container.audit.list_recent(limit=limit, offset=0)
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["id", "occurred_at", "actor", "event", "details_json", "run_id"])
        for row in rows:
            details = row.get("details") or {}
            run_id = details.get("run_id") if isinstance(details, dict) else ""
            writer.writerow(
                [
                    csv_safe_cell(row.get("id")),
                    csv_safe_cell(row.get("occurred_at")),
                    csv_safe_cell(row.get("actor")),
                    csv_safe_cell(row.get("event")),
                    csv_safe_cell(json.dumps(details, ensure_ascii=False, default=str)),
                    csv_safe_cell(run_id or ""),
                ]
            )
        buffer.seek(0)
        return StreamingResponse(
            iter([buffer.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="compass-activity.csv"'},
        )

    @router.get("/api/approvals")
    def approvals(
        status: str = Query(default="pending"),
        limit: int = Query(default=50, ge=1, le=200),
    ) -> list[dict[str, Any]]:
        wanted: ApprovalStatus | None
        try:
            wanted = None if status == "all" else ApprovalStatus(status)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unknown approval status.") from exc
        return [
            approval_payload_row(item)
            for item in container.approval_service.list_approvals(wanted, limit=limit)
        ]

    @router.post("/api/approvals/bulk-approve")
    def bulk_approve_low_risk() -> dict[str, Any]:
        """Approve every pending low-risk approval at once. Anything medium/high or carrying
        untrusted content stays for a one-by-one decision."""
        now = datetime.now(UTC)
        approved, skipped = [], 0
        for item in container.approval_service.list_approvals(ApprovalStatus.PENDING, limit=200):
            if item.is_expired(now) or item.risk != "low" or item.untrusted_content:
                skipped += 1
                continue
            try:
                container.approval_service.decide(
                    item.id, True, actor=DASHBOARD_OWNER, channel="dashboard"
                )
                approved.append(item.id)
            except (StorageError, ApprovalForbiddenError, ApprovalConflictError):
                skipped += 1
        return {"approved": approved, "skipped": skipped}

    @router.get("/api/approvals/{approval_id}")
    def get_approval(approval_id: str) -> dict[str, Any]:
        try:
            return approval_payload_row(container.approval_service.get(approval_id))
        except StorageError as exc:
            raise approval_error(exc) from exc

    @router.post("/api/approvals/{approval_id}/decision")
    def decide_approval(approval_id: str, request: ApprovalDecisionRequest) -> dict[str, Any]:
        try:
            outcome = container.approval_service.decide(
                approval_id, request.approve, actor=DASHBOARD_OWNER, channel="dashboard"
            )
        except (StorageError, ApprovalForbiddenError, ApprovalConflictError) as exc:
            raise approval_error(exc) from exc
        return {
            "id": approval_id,
            "decision": outcome.decision,
            "status": outcome.approval.status.value,
            "executed": outcome.executed,
            "ok": outcome.ok,
            "result": outcome.output,
            "run_id": outcome.approval.run_id,
            "approval": approval_payload_row(outcome.approval),
        }

    @router.post("/api/approvals/{approval_id}/edit", status_code=201)
    def edit_approval(approval_id: str, request: ApprovalEditRequest) -> dict[str, Any]:
        try:
            replacement = container.approval_service.edit(
                approval_id, request.arguments, actor=DASHBOARD_OWNER, channel="dashboard"
            )
        except (
            StorageError,
            ApprovalForbiddenError,
            ApprovalConflictError,
            ToolInputError,
        ) as exc:
            raise approval_error(exc) from exc
        return approval_payload_row(replacement)

    return router
