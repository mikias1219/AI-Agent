"""Build structured daily briefing context through the tool registry (AUT-02, AG-RTN-03)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any

from personal_agent.application.agent import Agent
from personal_agent.application.run_events import emit_event
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.dates import get_zone
from personal_agent.domain.models import (
    AgentRun,
    Message,
    RunStatus,
    ToolCall,
    ToolContext,
)
from personal_agent.domain.ports import (
    AgentRunRepository,
    ApprovalStore,
    EventSink,
    ToolRegistry,
)
from personal_agent.domain.task_rules import TaskView
from personal_agent.prompts import render_briefing_prompt

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BriefingItem:
    title: str
    time: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class BriefingSection:
    id: str
    heading: str
    status: str  # ok | empty | not_connected | unavailable | error
    summary: str
    items: list[BriefingItem] = field(default_factory=list)


@dataclass(slots=True)
class BriefingDocument:
    text: str
    summary: str
    sections: list[BriefingSection]
    sources: dict[str, str]
    run_id: str | None = None
    model: str = ""
    prompt_version: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "text": self.text,
            "summary": self.summary,
            "sections": [
                {
                    "id": s.id,
                    "heading": s.heading,
                    "status": s.status,
                    "summary": s.summary,
                    "items": [asdict(i) for i in s.items],
                }
                for s in self.sections
            ],
            "sources": dict(self.sources),
            "run_id": self.run_id,
            "model": self.model,
            "prompt_version": self.prompt_version,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_payload(), ensure_ascii=False)

    @staticmethod
    def from_stored(raw: str) -> BriefingDocument | None:
        raw = (raw or "").strip()
        if not raw:
            return None
        if raw.startswith("{"):
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                return BriefingDocument(text=raw, summary=raw, sections=[], sources={}, run_id=None)
            sections = [
                BriefingSection(
                    id=str(s.get("id", "")),
                    heading=str(s.get("heading", "")),
                    status=str(s.get("status", "ok")),
                    summary=str(s.get("summary", "")),
                    items=[
                        BriefingItem(
                            title=str(i.get("title", "")),
                            time=i.get("time"),
                            detail=i.get("detail"),
                        )
                        for i in (s.get("items") or [])
                    ],
                )
                for s in (data.get("sections") or [])
            ]
            return BriefingDocument(
                text=str(data.get("text") or data.get("summary") or ""),
                summary=str(data.get("summary") or data.get("text") or ""),
                sections=sections,
                sources=dict(data.get("sources") or {}),
                run_id=data.get("run_id"),
                model=str(data.get("model") or ""),
                prompt_version=str(data.get("prompt_version") or ""),
            )
        return BriefingDocument(text=raw, summary=raw, sections=[], sources={})


class BriefingBuilder:
    """Gathers real sources via the registry, then runs the agent with briefing_v1."""

    def __init__(
        self,
        *,
        agent: Agent,
        registry: ToolRegistry,
        tasks: TaskService,
        profiles: ProfileService,
        approvals: ApprovalStore | None = None,
        runs: AgentRunRepository | None = None,
        events: EventSink | None = None,
        google_connected: Callable[[], bool] | None = None,
        model_label: str = "fake",
    ) -> None:
        self._agent = agent
        self._registry = registry
        self._tasks = tasks
        self._profiles = profiles
        self._approvals = approvals
        self._runs = runs
        self._events = events
        self._google_connected = google_connected or (lambda: False)
        self._model_label = model_label

    def build(self, owner_id: str, now: datetime) -> BriefingDocument:
        timezone = self._profiles.timezone_for(owner_id)
        local = now.astimezone(get_zone(timezone))
        profile = self._profiles.get(owner_id)
        language = getattr(profile, "language", None) or "en"
        owner_name = getattr(profile, "name", None)

        prompt = render_briefing_prompt(
            today=local.date(),
            timezone=timezone,
            language=language,
            owner_name=owner_name,
        )

        run = AgentRun(
            id=uuid.uuid4().hex,
            session_id="",
            user_id=owner_id,
            origin="automation",
            prompt_version=prompt.version,
            status=RunStatus.RUNNING,
            input_text="daily_briefing",
            model=self._model_label,
            created_at=now,
        )
        if self._runs is not None:
            self._runs.create(run)

        ctx = ToolContext(
            user_id=owner_id,
            session_id=f"briefing:{run.id}",
            origin="automation",
            run_id=run.id,
            events=self._events,
        )
        emit_event(
            ctx,
            "run.started",
            origin="automation",
            prompt_version=prompt.version,
            model=run.model,
        )

        sections: list[BriefingSection] = []
        sources: dict[str, str] = {}

        calendar = self._calendar_section(ctx)
        sections.append(calendar)
        sources["calendar"] = calendar.status

        tasks_section = self._tasks_section(owner_id, timezone)
        sections.append(tasks_section)
        sources["tasks"] = tasks_section.status

        approvals_section = self._approvals_section()
        sections.append(approvals_section)
        sources["approvals"] = approvals_section.status

        email = self._email_section(ctx)
        sections.append(email)
        sources["email"] = email.status

        source_payload = {
            "date": local.strftime("%A %d %B %Y"),
            "timezone": timezone,
            "sections": [
                {
                    "id": s.id,
                    "heading": s.heading,
                    "status": s.status,
                    "summary": s.summary,
                    "items": [asdict(i) for i in s.items],
                }
                for s in sections
            ],
        }
        history = [
            Message(role="system", content=prompt.text),
            Message(
                role="user",
                content=(
                    "Compose today's daily briefing from this verified source data only:\n"
                    + json.dumps(source_payload, ensure_ascii=False)
                ),
            ),
        ]

        summary = ""
        try:
            outcome = self._agent.run_turn(history, ctx)
            summary = (outcome.final_text or "").strip()
        except Exception as exc:  # noqa: BLE001 — briefing must still return sections
            logger.exception("Briefing agent run failed")
            summary = f"Briefing sources were gathered, but the model could not finish: {exc}"
            if self._runs is not None:
                run.status = RunStatus.FAILED
                run.error = str(exc)
                run.finished_at = now
                self._runs.save(run)
            emit_event(ctx, "run.failed", status="failed", error=str(exc))
            text = self._render_text(local, sections, summary)
            return BriefingDocument(
                text=text,
                summary=summary,
                sections=sections,
                sources=sources,
                run_id=run.id,
                model=run.model,
                prompt_version=prompt.version,
            )

        text = self._render_text(local, sections, summary)
        run.status = RunStatus.COMPLETED
        run.final_text = text
        run.finished_at = now
        if self._runs is not None:
            self._runs.save(run)
        emit_event(ctx, "run.completed", status="completed", reply=text)
        return BriefingDocument(
            text=text,
            summary=summary or text,
            sections=sections,
            sources=sources,
            run_id=run.id,
            model=run.model,
            prompt_version=prompt.version,
        )

    def _calendar_section(self, ctx: ToolContext) -> BriefingSection:
        if not self._google_connected():
            return BriefingSection(
                id="calendar",
                heading="Calendar",
                status="not_connected",
                summary="Calendar is not connected.",
            )
        if not self._tool_registered("google_calendar_list"):
            return BriefingSection(
                id="calendar",
                heading="Calendar",
                status="unavailable",
                summary="Calendar tool is unavailable.",
            )
        result = self._call_tool(ctx, "google_calendar_list", {"page": 1, "page_size": 20})
        if not result["ok"]:
            return BriefingSection(
                id="calendar",
                heading="Calendar",
                status="error",
                summary=f"Calendar could not be read: {result['error']}",
            )
        items = self._parse_calendar_items(result["output"])
        if not items:
            return BriefingSection(
                id="calendar",
                heading="Calendar",
                status="empty",
                summary="No events found for the connected calendar.",
            )
        return BriefingSection(
            id="calendar",
            heading="Calendar",
            status="ok",
            summary=f"{len(items)} event(s) on the connected calendar.",
            items=items,
        )

    def _email_section(self, ctx: ToolContext) -> BriefingSection:
        if not self._google_connected():
            return BriefingSection(
                id="email",
                heading="Email",
                status="not_connected",
                summary="Gmail is not connected.",
            )
        if not self._tool_registered("google_gmail_search"):
            return BriefingSection(
                id="email",
                heading="Email",
                status="unavailable",
                summary="Gmail tool is unavailable.",
            )
        result = self._call_tool(
            ctx,
            "google_gmail_search",
            {"query": "is:unread newer_than:1d", "max_results": 5},
        )
        if not result["ok"]:
            return BriefingSection(
                id="email",
                heading="Email",
                status="error",
                summary=f"Email could not be read: {result['error']}",
            )
        items = self._parse_email_items(result["output"])
        if not items:
            return BriefingSection(
                id="email",
                heading="Email",
                status="empty",
                summary="No important unread email found.",
            )
        return BriefingSection(
            id="email",
            heading="Email",
            status="ok",
            summary=f"{len(items)} unread message(s).",
            items=items,
        )

    def _tasks_section(self, owner_id: str, timezone: str) -> BriefingSection:
        due = self._tasks.list(view=TaskView.TODAY, timezone=timezone, owner_user_id=owner_id)
        overdue = self._tasks.list(view=TaskView.OVERDUE, timezone=timezone, owner_user_id=owner_id)
        items: list[BriefingItem] = []
        for task in overdue[:10]:
            items.append(BriefingItem(title=task.title, detail="overdue"))
        for task in due[:10]:
            items.append(BriefingItem(title=task.title, detail="due today"))
        if not items:
            return BriefingSection(
                id="tasks",
                heading="Tasks",
                status="empty",
                summary="Nothing due today.",
            )
        return BriefingSection(
            id="tasks",
            heading="Tasks",
            status="ok",
            summary=f"{len(overdue)} overdue, {len(due)} due today.",
            items=items,
        )

    def _approvals_section(self) -> BriefingSection:
        pending = 0
        if self._approvals is not None:
            from personal_agent.domain.approvals import ApprovalStatus

            pending = len(self._approvals.find(status=ApprovalStatus.PENDING, limit=50))
        if pending == 0:
            return BriefingSection(
                id="approvals",
                heading="Approvals",
                status="empty",
                summary="No pending approvals.",
            )
        return BriefingSection(
            id="approvals",
            heading="Approvals",
            status="ok",
            summary=f"{pending} pending approval(s).",
            items=[BriefingItem(title=f"{pending} waiting for your decision")],
        )

    def _tool_registered(self, name: str) -> bool:
        return any(spec.name == name for spec in self._registry.specs())

    def _call_tool(
        self, ctx: ToolContext, name: str, arguments: Mapping[str, Any]
    ) -> dict[str, Any]:
        call = ToolCall(id=uuid.uuid4().hex, name=name, arguments=dict(arguments))
        emit_event(ctx, "tool.started", call_id=call.id, name=name, arguments=dict(arguments))
        try:
            result = self._registry.execute(call, ctx)
        except Exception as exc:  # noqa: BLE001 — one failed source must not fail briefing
            emit_event(
                ctx,
                "tool.finished",
                call_id=call.id,
                name=name,
                ok=False,
                output=str(exc),
                duration_ms=0,
            )
            return {"ok": False, "error": str(exc), "output": ""}
        content = result.output if result.ok else (result.error or "tool failed")
        emit_event(
            ctx,
            "tool.finished",
            call_id=call.id,
            name=name,
            ok=result.ok,
            output=content,
            duration_ms=0,
        )
        return {"ok": result.ok, "error": result.error or "", "output": result.output}

    @staticmethod
    def _parse_calendar_items(raw: str) -> list[BriefingItem]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        rows = data.get("items") or data.get("events") or data.get("results") or []
        if isinstance(data, list):
            rows = data
        items: list[BriefingItem] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            title = str(row.get("summary") or row.get("title") or row.get("subject") or "").strip()
            if not title:
                continue
            start = (
                row.get("start") or row.get("starts_at") or row.get("startsAt") or row.get("time")
            )
            if isinstance(start, Mapping):
                start = start.get("dateTime") or start.get("date")
            items.append(BriefingItem(title=title, time=str(start) if start else None))
        return items

    @staticmethod
    def _parse_email_items(raw: str) -> list[BriefingItem]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        rows = data.get("items") or data.get("messages") or data.get("results") or []
        if isinstance(data, list):
            rows = data
        items: list[BriefingItem] = []
        for row in rows:
            if not isinstance(row, Mapping):
                continue
            title = str(row.get("subject") or row.get("title") or "").strip()
            if not title:
                continue
            detail = str(row.get("from") or row.get("snippet") or "").strip() or None
            items.append(BriefingItem(title=title, detail=detail))
        return items

    @staticmethod
    def _render_text(local: datetime, sections: list[BriefingSection], summary: str) -> str:
        lines = [f"Daily briefing — {local.strftime('%A %d %B %Y')}", ""]
        if summary and summary not in ("Okay.", "OK."):
            lines.append(summary)
            lines.append("")
        for section in sections:
            lines.append(f"{section.heading}: {section.summary}")
            for item in section.items:
                stamp = f" ({item.time})" if item.time else ""
                extra = f" — {item.detail}" if item.detail else ""
                lines.append(f"- {item.title}{stamp}{extra}")
            lines.append("")
        return "\n".join(lines).strip()
