"""Goals and plans (spec §9.2): entities, statuses, and the approval rule.

Approving a plan authorizes its READ/PREPARE steps only. Any step whose access kind is
`execute` or `destructive` is a hard ceiling: approval parks it as `needs_ok` and it can only
run later through the tool registry's own approval gate (BR-01..BR-14). Nothing here imports
infrastructure, application or presentation code.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime

GOAL_STATUSES: frozenset[str] = frozenset({"active", "paused", "done"})
PLAN_STEP_STATUSES: frozenset[str] = frozenset({"planned", "running", "needs_ok", "done", "failed"})
PLAN_STATUSES: frozenset[str] = frozenset({"proposed", "approved", "done", "cancelled"})

# Ordered from least to most powerful; a step is never trusted below what its tool really is.
ACCESS_ORDER: tuple[str, ...] = ("read", "prepare", "execute", "destructive")
# Access kinds a plan approval may authorize. Everything else needs its own approval.
AUTHORIZED_BY_PLAN_APPROVAL: frozenset[str] = frozenset({"read", "prepare"})

MAX_TITLE = 256
MAX_CRITERIA = 20
MAX_STEPS = 30


class GoalError(ValueError):
    """A goal or plan rule was violated (bad input or illegal state change)."""


@dataclass(slots=True)
class Goal:
    id: str
    owner_user_id: str
    title: str
    success_criteria: list[str]
    progress: float
    status: str  # active | paused | done
    next_step: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(slots=True)
class PlanStep:
    id: str
    title: str
    tool_name: str | None
    access_kind: str
    status: str  # planned | running | needs_ok | done | failed
    depends_on: list[str] = field(default_factory=list)


@dataclass(slots=True)
class Plan:
    id: str
    goal_id: str | None
    owner_user_id: str
    steps: list[PlanStep]
    status: str  # proposed | approved | done | cancelled
    title: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None


# -- validation -----------------------------------------------------------------


def clean_title(raw: str, *, what: str = "Title") -> str:
    title = (raw or "").strip()
    if not title:
        raise GoalError(f"{what} is required.")
    if len(title) > MAX_TITLE:
        raise GoalError(f"{what} must be at most {MAX_TITLE} characters.")
    return title


def clean_criteria(raw: Iterable[str] | None) -> list[str]:
    items = [str(c).strip() for c in (raw or []) if str(c).strip()]
    if len(items) > MAX_CRITERIA:
        raise GoalError(f"At most {MAX_CRITERIA} success criteria.")
    return items


def clean_progress(raw: float) -> float:
    value = float(raw)
    if not 0.0 <= value <= 1.0:
        raise GoalError("Progress must be between 0 and 1.")
    return value


def check_goal_status(raw: str) -> str:
    if raw not in GOAL_STATUSES:
        raise GoalError(f"Unknown goal status '{raw}'. Use active, paused, or done.")
    return raw


def check_access_kind(raw: str) -> str:
    if raw not in ACCESS_ORDER:
        raise GoalError(f"Unknown access kind '{raw}'. Use read, prepare, execute, or destructive.")
    return raw


def stricter_access(declared: str, actual: str | None) -> str:
    """The more powerful of what a step claims and what its tool really is.

    A plan author (the model) cannot downgrade a tool by mislabelling its step.
    """
    declared = check_access_kind(declared)
    if actual is None:
        return declared
    actual = check_access_kind(actual)
    return max(declared, actual, key=ACCESS_ORDER.index)


def needs_separate_approval(access_kind: str) -> bool:
    """Hard ceilings: execute and destructive steps never ride on a plan approval."""
    return access_kind not in AUTHORIZED_BY_PLAN_APPROVAL


def validate_steps(steps: list[PlanStep]) -> None:
    """Steps need titles, unique ids, known statuses, and dependencies that exist earlier."""
    if not steps:
        raise GoalError("A plan needs at least one step.")
    if len(steps) > MAX_STEPS:
        raise GoalError(f"A plan has at most {MAX_STEPS} steps.")
    seen: set[str] = set()
    for step in steps:
        clean_title(step.title, what="Step title")
        if step.id in seen:
            raise GoalError(f"Duplicate step id '{step.id}'.")
        if step.status not in PLAN_STEP_STATUSES:
            raise GoalError(f"Unknown step status '{step.status}'.")
        check_access_kind(step.access_kind)
        for dep in step.depends_on:
            if dep not in seen:
                raise GoalError(f"Step '{step.id}' depends on unknown or later step '{dep}'.")
        seen.add(step.id)


# -- the approval rule -----------------------------------------------------------


def approve_plan(plan: Plan, *, now: datetime) -> Plan:
    """Authorize READ/PREPARE steps; park execute/destructive steps as `needs_ok`.

    Never runs anything and never marks a hard-ceiling step as authorized.
    """
    if plan.status != "proposed":
        raise GoalError(f"Only a proposed plan can be approved (this plan is {plan.status}).")
    for step in plan.steps:
        if step.status != "planned":
            continue
        if needs_separate_approval(step.access_kind):
            step.status = "needs_ok"
    plan.status = "approved"
    plan.approved_at = now
    plan.updated_at = now
    return plan


def cancel_plan(plan: Plan, *, now: datetime) -> Plan:
    if plan.status in ("done", "cancelled"):
        raise GoalError(f"This plan is already {plan.status}.")
    plan.status = "cancelled"
    plan.updated_at = now
    return plan


def authorized_steps(plan: Plan) -> list[PlanStep]:
    """Steps an approved plan may run without asking again (read/prepare, still planned)."""
    if plan.status != "approved":
        return []
    return [
        s
        for s in plan.steps
        if s.status == "planned" and s.access_kind in AUTHORIZED_BY_PLAN_APPROVAL
    ]


__all__ = [
    "ACCESS_ORDER",
    "AUTHORIZED_BY_PLAN_APPROVAL",
    "GOAL_STATUSES",
    "MAX_STEPS",
    "PLAN_STATUSES",
    "PLAN_STEP_STATUSES",
    "Goal",
    "GoalError",
    "Plan",
    "PlanStep",
    "approve_plan",
    "authorized_steps",
    "cancel_plan",
    "check_access_kind",
    "check_goal_status",
    "clean_criteria",
    "clean_progress",
    "clean_title",
    "needs_separate_approval",
    "stricter_access",
    "validate_steps",
]
