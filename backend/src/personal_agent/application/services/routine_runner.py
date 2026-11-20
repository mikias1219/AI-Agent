"""Run catalogue routines that are not the daily briefing (G3 / G2)."""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.routine_catalog import catalogue_by_kind
from personal_agent.application.services.suggestion_service import SuggestionService
from personal_agent.application.services.task_service import TaskService
from personal_agent.domain.models import (
    AgentRun,
    Message,
    RunStatus,
    ToolCall,
    ToolContext,
)
from personal_agent.domain.ports import AgentRunRepository, EventSink, ToolRegistry
from personal_agent.domain.scheduler import Automation
from personal_agent.domain.task_rules import TaskView

logger = logging.getLogger(__name__)


class RoutineRunner:
    """Executes a non-briefing automation: deterministic handlers or a bounded agent turn."""

    def __init__(
        self,
        *,
        agent: Any,
        registry: ToolRegistry,
        suggestions: SuggestionService,
        tasks: TaskService,
        profiles: ProfileService,
        runs: AgentRunRepository | None = None,
        events: EventSink | None = None,
        google_connected: Callable[[], bool] | None = None,
        model_label: str = "fake",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._agent = agent
        self._registry = registry
        self._suggestions = suggestions
        self._tasks = tasks
        self._profiles = profiles
        self._runs = runs
        self._events = events
        self._google_connected = google_connected or (lambda: False)
        self._model_label = model_label
        self._clock = clock or (lambda: datetime.now(UTC))

    def run(self, automation: Automation, now: datetime | None = None) -> dict[str, Any]:
        now = now or self._clock()
        spec = catalogue_by_kind().get(automation.kind)
        if spec is None:
            raise ValueError(f"Unknown routine kind '{automation.kind}'.")
        if spec.uses_briefing_builder:
            raise ValueError("daily_briefing must use BriefingBuilder, not RoutineRunner.")

        if spec.handler == "inbox_triage":
            return self._inbox_triage(automation, now)
        if spec.handler == "deadline_guard":
            return self._deadline_guard(automation, now)
        return self._agent_routine(automation, spec.prompt, now)

    def _inbox_triage(self, automation: Automation, now: datetime) -> dict[str, Any]:
        owner = automation.owner_user_id
        if not self._google_connected():
            return {
                "summary": "Gmail is not connected — inbox triage skipped.",
                "proposed": 0,
                "run_id": None,
            }
        ctx = ToolContext(
            user_id=owner,
            session_id=f"routine:{automation.id}",
            origin="automation",
        )
        listing = self._call(ctx, "google_gmail_search", {"query": "is:unread newer_than:2d", "max_results": 8})
        if not listing["ok"]:
            return {
                "summary": f"Could not read Gmail: {listing['error']}",
                "proposed": 0,
                "run_id": None,
            }
        messages = self._parse_messages(listing["output"])
        proposed = 0
        for message in messages[:3]:
            message_id = str(message.get("id") or "").strip()
            subject = str(message.get("subject") or "Message").strip() or "Message"
            sender = str(message.get("from") or "unknown").strip()
            if not message_id:
                continue
            if len(self._suggestions.open(owner)) >= 5:
                break
            snippet = str(message.get("snippet") or message.get("body") or "")[:240]
            draft = (
                f"Thanks for your note about “{subject}”. "
                "I’ll follow up shortly — please edit this draft before sending."
            )
            reply_args: dict[str, Any] = {"message_id": message_id, "body": draft}
            if "@" in sender:
                reply_args["to"] = sender
            reply_args["subject"] = (
                subject if subject.lower().startswith("re:") else f"Re: {subject}"
            )
            try:
                self._suggestions.create(
                    owner,
                    kind="mail_reply",
                    title=f"Reply: {subject}",
                    reason=snippet or f"Unread mail from {sender} may need a reply.",
                    source=f"gmail: '{subject}' from {sender}",
                    proposed_action={
                        "tool_name": "google_gmail_reply",
                        "arguments": reply_args,
                    },
                    expires_in=timedelta(days=2),
                    origin="automation",
                )
                proposed += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("mail_reply suggestion failed: %s", exc)
        summary = (
            f"Inbox triage proposed {proposed} mail reply suggestion(s)."
            if proposed
            else "Inbox triage found nothing that clearly needs a reply."
        )
        return {"summary": summary, "proposed": proposed, "run_id": None}

    def _deadline_guard(self, automation: Automation, now: datetime) -> dict[str, Any]:
        owner = automation.owner_user_id
        timezone = self._profiles.timezone_for(owner)
        overdue = list(self._tasks.list(view=TaskView.OVERDUE, timezone=timezone, owner_user_id=owner))
        today = list(self._tasks.list(view=TaskView.TODAY, timezone=timezone, owner_user_id=owner))
        proposed = 0
        for task in (overdue + today)[:3]:
            if len(self._suggestions.open(owner)) >= 5:
                break
            label = "overdue" if task in overdue else "due today"
            try:
                self._suggestions.create(
                    owner,
                    kind="deadline",
                    title=f"Check task: {task.title}",
                    reason=f"This task is {label}.",
                    source=f"task: {task.title}",
                    proposed_action={},
                    expires_in=timedelta(days=1),
                    origin="automation",
                )
                proposed += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("deadline suggestion failed: %s", exc)
        summary = (
            f"Deadline guard proposed {proposed} suggestion(s)."
            if proposed
            else "No overdue or due-today tasks to surface."
        )
        return {"summary": summary, "proposed": proposed, "run_id": None}

    def _agent_routine(self, automation: Automation, prompt: str, now: datetime) -> dict[str, Any]:
        owner = automation.owner_user_id
        run = AgentRun(
            id=uuid.uuid4().hex,
            session_id="",
            user_id=owner,
            origin="automation",
            prompt_version=f"routine_{automation.kind}",
            status=RunStatus.RUNNING,
            input_text=automation.kind,
            model=self._model_label,
            created_at=now,
        )
        if self._runs is not None:
            self._runs.create(run)
        ctx = ToolContext(
            user_id=owner,
            session_id=f"routine:{run.id}",
            origin="automation",
            run_id=run.id,
            events=self._events,
        )
        history = [
            Message(role="system", content=prompt),
            Message(
                role="user",
                content=f"Run the {automation.kind} routine now. Use tools; do not invent data.",
            ),
        ]
        try:
            outcome = self._agent.run_turn(history, ctx)
            text = (outcome.final_text or "").strip() or f"{automation.kind} finished."
            run.status = RunStatus.COMPLETED
            run.final_text = text
            run.finished_at = now
        except Exception as exc:  # noqa: BLE001
            logger.exception("Routine %s failed", automation.kind)
            text = f"Routine failed: {exc}"
            run.status = RunStatus.FAILED
            run.error = str(exc)
            run.finished_at = now
        if self._runs is not None:
            self._runs.save(run)
        return {"summary": text, "proposed": None, "run_id": run.id}

    def _call(self, ctx: ToolContext, name: str, arguments: Mapping[str, Any]) -> dict[str, Any]:
        call = ToolCall(id=uuid.uuid4().hex, name=name, arguments=dict(arguments))
        try:
            result = self._registry.execute(call, ctx)
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc), "output": ""}
        return {"ok": result.ok, "error": result.error or "", "output": result.output}

    @staticmethod
    def _parse_messages(raw: str) -> list[dict[str, Any]]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return []
        rows = data.get("items") or data.get("messages") or data.get("results") or []
        if isinstance(data, list):
            rows = data
        return [row for row in rows if isinstance(row, Mapping)]


__all__ = ["RoutineRunner"]
