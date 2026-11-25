"""Built-in routine catalogue (AG-RTN). Seeded disabled except daily briefing.

Each kind has a schedule default, owner-facing label, and a prompt the routine runner uses.
No free-form builder — owners enable or disable catalogue rows.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoutineKind:
    kind: str
    label: str
    description: str
    schedule_time: str
    enabled_by_default: bool
    prompt: str
    # When True, the scheduler uses BriefingBuilder instead of the generic agent runner.
    uses_briefing_builder: bool = False
    # Deterministic handler name in RoutineRunner (None = agent prompt only).
    handler: str | None = None


CATALOGUE: tuple[RoutineKind, ...] = (
    RoutineKind(
        kind="daily_briefing",
        label="Morning briefing",
        description="Calendar, tasks, approvals and email into one morning summary.",
        schedule_time="08:00",
        enabled_by_default=True,
        prompt="",
        uses_briefing_builder=True,
    ),
    RoutineKind(
        kind="inbox_triage",
        label="Inbox triage",
        description="Read recent mail and propose reply drafts under Needs you → Mail replies.",
        schedule_time="09:00",
        enabled_by_default=False,
        prompt=(
            "You are running the inbox triage routine. Read recent important unread mail with "
            "google_gmail_search and google_gmail_read. For each message that looks like it needs "
            "a reply (questions, requests, deadlines), call suggestion_propose with kind "
            "mail_reply, a clear title, reason, and a source citation naming the subject and "
            "sender. Prefer proposed tool google_gmail_reply with message_id and a short draft "
            "body the owner can edit when approving. Cap at three proposals. Never send mail."
        ),
        handler="inbox_triage",
    ),
    RoutineKind(
        kind="evening_wrapup",
        label="Evening wrap-up",
        description="What moved today and what still needs you tomorrow.",
        schedule_time="18:00",
        enabled_by_default=False,
        prompt=(
            "You are running the evening wrap-up. Use task tools and calendar reads to summarise "
            "what was due today and what remains. If something needs the owner tomorrow, call "
            "suggestion_propose with kind followup and a real source citation. Do not invent "
            "events or mail. Keep proposals to at most two."
        ),
    ),
    RoutineKind(
        kind="weekly_review",
        label="Weekly review",
        description="Goals, open plans and overdue work for the week.",
        schedule_time="09:00",
        enabled_by_default=False,
        prompt=(
            "You are running the weekly review. Look at goals, plans and overdue tasks. Propose "
            "at most two suggestion_propose items (kind followup or deadline) with real sources. "
            "Do not invent data."
        ),
    ),
    RoutineKind(
        kind="deadline_guard",
        label="Deadline guard",
        description="Surface overdue and soon-due tasks as suggestions.",
        schedule_time="10:00",
        enabled_by_default=False,
        prompt=(
            "You are running deadline guard. List overdue and due-soon tasks. For each urgent "
            "item, call suggestion_propose with kind deadline, citing the task title as source. "
            "At most three proposals. Do not invent tasks."
        ),
        handler="deadline_guard",
    ),
    RoutineKind(
        kind="daily_wrapup",
        label="Daily wrap-up",
        description=(
            "Scores your day, offers to carry unfinished tasks to tomorrow and, when Drive or "
            "Calendar sync is on, asks to back up the day."
        ),
        schedule_time="21:00",
        enabled_by_default=False,
        prompt="",
        handler="daily_wrapup",
    ),
    RoutineKind(
        kind="learning_daily",
        label="Daily learning",
        description="A nudge when words or facts are due for review.",
        schedule_time="19:00",
        enabled_by_default=False,
        prompt="",
        handler="life_nudge",
    ),
    RoutineKind(
        kind="reading_daily",
        label="Daily reading",
        description="Today's reference from your active reading plan.",
        schedule_time="07:00",
        enabled_by_default=False,
        prompt="",
        handler="life_nudge",
    ),
    RoutineKind(
        kind="diary_nudge",
        label="Diary nudge",
        description="A gentle reminder when you have not written in your diary today.",
        schedule_time="21:00",
        enabled_by_default=False,
        prompt="",
        handler="life_nudge",
    ),
)


def catalogue_by_kind() -> dict[str, RoutineKind]:
    return {row.kind: row for row in CATALOGUE}


def label_for(kind: str) -> str:
    row = catalogue_by_kind().get(kind)
    return row.label if row else kind.replace("_", " ").title()


__all__ = ["CATALOGUE", "RoutineKind", "catalogue_by_kind", "label_for"]
