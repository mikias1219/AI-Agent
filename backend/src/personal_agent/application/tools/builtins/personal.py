"""Cross-module read tools, habits and finance tools (roadmap sections 6.8 and 7).

Money writes use the `financial` access kind: always approval, never auto-approved.
Agent answers come only from these results; missing data is reported, never estimated.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import Any

from personal_agent.application.goal_payloads import goal_payload
from personal_agent.application.services.day_service import DayService, parse_day
from personal_agent.application.services.finance_service import FinanceService
from personal_agent.application.services.goal_service import GoalService
from personal_agent.application.services.habit_service import HabitService
from personal_agent.application.services.inbox_service import InboxService
from personal_agent.application.services.review_service import ReviewService
from personal_agent.application.services.time_service import TimeService
from personal_agent.domain.exceptions import ToolInputError
from personal_agent.domain.finance import format_money, tx_payload
from personal_agent.domain.life import LifeError
from personal_agent.domain.models import ToolContext, ToolSpec

Handler = Callable[[ToolContext, Mapping[str, Any]], str]


def _guard(fn: Handler) -> Handler:
    """Turn domain validation errors into tool input errors the model can correct."""

    def wrapped(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        try:
            return fn(ctx, args)
        except LifeError as exc:
            raise ToolInputError(str(exc)) from exc

    return wrapped


def _obj(
    properties: dict[str, Any] | None = None, required: list[str] | None = None
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties or {},
        "required": required or [],
        "additionalProperties": False,
    }


_AMOUNT = {"type": ["number", "string"], "description": "Amount in major units, e.g. 250 or 250.50"}
_PERIOD = {"type": "string", "pattern": "^\\d{4}-\\d{2}$", "description": "Month, e.g. 2026-11"}
_RULE = {
    "type": "object",
    "properties": {
        "freq": {"type": "string", "enum": ["daily", "weekly", "monthly", "quarterly", "yearly"]},
        "interval": {"type": "integer", "minimum": 1, "maximum": 365},
        "weekdays": {"type": "array", "items": {"type": "integer", "minimum": 0, "maximum": 6}},
        "day_of_month": {"type": "integer", "minimum": 1, "maximum": 31},
        "start": {"type": "string"},
        "end": {"type": "string"},
    },
    "required": ["freq"],
    "additionalProperties": False,
}


def personal_tools(
    *,
    habits: HabitService,
    finance: FinanceService,
    goals: GoalService,
    days: DayService,
    inbox: InboxService | None,
    review: ReviewService,
    time: TimeService,
) -> list[ToolSpec]:
    # -- cross-module reads ---------------------------------------------------------

    def goal_list(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        found = goals.list(ctx.user_id, args.get("status"))
        items = [goal_payload(g) for g in found]
        text = f"{len(items)} goal(s)." if items else "No goals yet."
        return json.dumps({"summary": text, "goals": items})

    def goal_progress(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        goal = goals.get(str(args["goal_id"]), ctx.user_id)
        data = goal_payload(goal)
        return json.dumps(
            {"summary": f"{goal.title}: {goal.progress}% ({goal.status}).", "goal": data}
        )

    def days_stats(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        stats = days.stats(ctx.user_id)
        week = stats["week"]
        return json.dumps(
            {"summary": f"Streak {stats['streak_days']} day(s); week {week}.", "stats": stats}
        )

    def week_review(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        data = review.build(ctx.user_id, str(args.get("period") or "week"))
        return json.dumps({"summary": f"Review {data['from']} to {data['to']}.", **data})

    def inbox_list(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        items = inbox.open_items(ctx.user_id, 20) if inbox else []
        slim = [
            {k: v for k, v in item.items() if k not in ("approval", "suggestion")} for item in items
        ]
        return json.dumps({"summary": f"{len(slim)} item(s) need you.", "items": slim})

    def life_snapshot(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        today = days.today(ctx.user_id)
        day = days.day(ctx.user_id, today)
        overdue = [
            t for t in days.tasks_until(ctx.user_id, today - timedelta(days=1))
            if t.status.value in ("planned", "in_progress", "blocked")
        ]  # fmt: skip
        snapshot = {
            "date": today.isoformat(),
            "events": day["events"],
            "tasks": day["tasks"],
            "task_summary": day["summary"],
            "overdue_count": len(overdue),
            "habits": habits.day_status(ctx.user_id),
            "money": finance.today_row(ctx.user_id),
            "goals": [goal_payload(g) for g in goals.active(ctx.user_id)][:5],
        }
        return json.dumps({"summary": f"Snapshot for {today.isoformat()}.", **snapshot})

    def time_summary(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        today = days.today(ctx.user_id)
        span = int(args.get("days") or 7)
        data = time.summary(ctx.user_id, today - timedelta(days=span - 1), today)
        hours = round(data["total_minutes"] / 60, 1)
        return json.dumps({"summary": f"{hours} h tracked in the last {span} day(s).", **data})

    def time_start(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        entry = time.start(
            ctx.user_id,
            task_id=args.get("task_id"),
            project=str(args.get("project") or ""),
            goal_id=args.get("goal_id"),
            note=str(args.get("note") or ""),
        )
        return json.dumps({"summary": "Timer started.", "entry_id": entry.id})

    def time_stop(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        entry = time.stop(ctx.user_id)
        return json.dumps(
            {"summary": f"Timer stopped: {entry.minutes(entry.ended_at or entry.started_at)} min."}
        )

    # -- habits -----------------------------------------------------------------------

    def habit_status(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        day = parse_day(args["date"], "date") if args.get("date") else None
        data = habits.day_status(ctx.user_id, day)
        text = f"{data['done']} of {data['due']} habit(s) done on {data['day']}."
        return json.dumps({"summary": text, **data})

    def habit_check_in(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        item = habits.check_in(
            ctx.user_id,
            str(args["habit_id"]),
            day=parse_day(args["date"], "date") if args.get("date") else None,
            status=str(args.get("status") or "done"),
            value=args.get("value"),
            note=str(args.get("note") or ""),
        )
        return json.dumps({"summary": f"Habit {item.status} for {item.day.isoformat()}.",
                           "habit_id": item.habit_id, "day": item.day.isoformat()})  # fmt: skip

    # -- finance reads / drafts -----------------------------------------------------

    def finance_summary(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        data = finance.summary(ctx.user_id, args.get("period"))
        text = (
            f"{data['period']}: income {format_money(data['income_minor'])}, "
            f"spent {format_money(data['spent_minor'])}, saved {format_money(data['saved_minor'])}."
        )
        return json.dumps({"summary": text, **data})

    def finance_query(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        data = finance.query(
            ctx.user_id,
            period=args.get("period"),
            category=str(args.get("category") or ""),
            merchant=str(args.get("merchant") or ""),
        )
        text = data["message"] or (
            f"{data['count']} transaction(s); spent {format_money(data['spent_minor'])}."
        )
        return json.dumps({"summary": text, **data})

    def finance_affordability(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        data = finance.affordability(ctx.user_id, args["amount"], str(args.get("category") or ""))
        verdict = "Affordable" if data["affordable"] else "Not affordable"
        return json.dumps({"summary": f"{verdict}: {data['note']}", **data})

    def finance_draft_transaction(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        if args.get("text"):
            draft = finance.parse(ctx.user_id, str(args["text"]))
        else:
            draft = {"draft": {k: v for k, v in args.items()}, "saved": False}
        return json.dumps(
            {"result_type": "finance_draft", "summary": "Draft transaction (not saved).", **draft}
        )

    def finance_draft_budget(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        return json.dumps(
            {"result_type": "finance_draft", "summary": "Draft budget (not saved).",
             "draft": dict(args), "saved": False}
        )  # fmt: skip

    # -- financial writes (always approved by a human) ------------------------------

    def finance_record_transaction(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        rows = finance.record(
            ctx.user_id, dict(args), created_by="agent", approval_id=ctx.approval_id
        )
        tx = rows[0]
        return json.dumps(
            {"summary": f"Recorded {tx.kind}: {format_money(tx.amount_minor, tx.currency)}.",
             "transaction": dict(tx_payload(tx))}
        )  # fmt: skip

    def finance_update_budget(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        budget = finance.set_lines(
            ctx.user_id, str(args["budget_id"]), args["lines"], approval_id=ctx.approval_id
        )
        return json.dumps({"summary": f"Updated budget {budget.name}.",
                           "budget": finance.budget_view(ctx.user_id, budget)})  # fmt: skip

    def finance_change_recurring(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        data = {k: v for k, v in args.items() if k != "rule_id"}
        rule = finance.change_recurring(
            ctx.user_id, str(args["rule_id"]), data, approval_id=ctx.approval_id
        )
        return json.dumps({"summary": f"Changed {rule.title} from its next occurrence "
                           f"(version {rule.version}).", "rule_id": rule.id})  # fmt: skip

    def finance_delete_transaction(ctx: ToolContext, args: Mapping[str, Any]) -> str:
        removed = finance.delete(ctx.user_id, str(args["transaction_id"]))
        return json.dumps(
            {"summary": f"Deleted {removed} transaction row(s) (recoverable 30 days)."}
        )

    tx_props = {
        "kind": {"type": "string", "enum": ["income", "expense", "transfer"]},
        "amount": _AMOUNT,
        "occurred_at": {"type": "string"},
        "account_id": {"type": "string"},
        "to_account_id": {"type": "string"},
        "category_id": {"type": "string"},
        "merchant": {"type": "string", "maxLength": 120},
        "note": {"type": "string", "maxLength": 500},
    }
    spec = ToolSpec
    return [
        spec(
            "goal_list",
            "List the owner's goals with progress and status.",
            _obj({"status": {"type": "string"}}),
            "read",
            _guard(goal_list),
            integration="goals",
        ),  # fmt: skip
        spec(
            "goal_progress",
            "Progress of one goal by id.",
            _obj({"goal_id": {"type": "string"}}, ["goal_id"]),
            "read",
            _guard(goal_progress),
            integration="goals",
        ),  # fmt: skip
        spec(
            "days_stats",
            "Task streak and week/month completion rates (productivity).",
            _obj(),
            "read",
            _guard(days_stats),
            integration="tasks",
        ),  # fmt: skip
        spec(
            "week_review",
            "Last 7 days across tasks, habits and money, for 'how was my week'.",
            _obj(),
            "read",
            _guard(week_review),
            integration="tasks",
        ),  # fmt: skip
        spec(
            "inbox_list",
            "Items waiting for the owner (approvals and suggestions).",
            _obj(),
            "read",
            _guard(inbox_list),
            integration="core",
        ),  # fmt: skip
        spec(
            "life_snapshot",
            "Today in one call: events, tasks, overdue count, habits, money, goals.",
            _obj(),
            "read",
            _guard(life_snapshot),
            integration="core",
        ),  # fmt: skip
        spec(
            "time_summary",
            "Where the owner's time went: minutes by day, project and task.",
            _obj({"days": {"type": "integer", "minimum": 1, "maximum": 90}}),
            "read",
            _guard(time_summary),
            integration="tasks",
        ),
        spec(
            "time_start",
            "Start the timer on a task, project or goal (stops any running timer).",
            _obj(
                {
                    "task_id": {"type": "string"},
                    "project": {"type": "string"},
                    "goal_id": {"type": "string"},
                    "note": {"type": "string", "maxLength": 300},
                }
            ),
            "prepare",
            _guard(time_start),
            integration="tasks",
        ),
        spec(
            "time_stop",
            "Stop the running timer.",
            _obj(),
            "prepare",
            _guard(time_stop),
            integration="tasks",
        ),
        spec(
            "habit_status",
            "Habits due on a day (default today) and their check-in state.",
            _obj({"date": {"type": "string"}}),
            "read",
            _guard(habit_status),
            integration="life",
        ),  # fmt: skip
        spec(
            "habit_check_in",
            "Check a habit in (done) or skip it with a reason for a day.",
            _obj(
                {
                    "habit_id": {"type": "string"},
                    "date": {"type": "string"},
                    "status": {"type": "string", "enum": ["done", "skipped"]},
                    "value": {"type": "number"},
                    "note": {"type": "string", "maxLength": 300},
                },
                ["habit_id"],
            ),
            "prepare",
            _guard(habit_check_in),
            integration="life",
        ),  # fmt: skip
        spec(
            "finance_summary",
            "Monthly money summary: income, spending, budget left, upcoming bills.",
            _obj({"period": _PERIOD}),
            "read",
            _guard(finance_summary),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_query",
            "Spend by period, category or merchant. Answers only from stored rows.",
            _obj(
                {"period": _PERIOD, "category": {"type": "string"}, "merchant": {"type": "string"}}
            ),
            "read",
            _guard(finance_query),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_affordability",
            "Can the owner afford a purchase? Impact on budget and end balance.",
            _obj({"amount": _AMOUNT, "category": {"type": "string"}}, ["amount"]),
            "read",
            _guard(finance_affordability),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_draft_transaction",
            "Draft a transaction from text ('lunch 250 cash') or fields. Never saves.",
            _obj({"text": {"type": "string"}, **tx_props}),
            "prepare",
            _guard(finance_draft_transaction),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_draft_budget",
            "Draft a monthly budget for the owner to review. Never saves.",
            _obj({"period": _PERIOD, "lines": {"type": "array", "items": {"type": "object"}}}),
            "prepare",
            _guard(finance_draft_budget),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_record_transaction",
            "Record income, an expense or a transfer. Money write: always needs approval.",
            _obj(tx_props, ["amount"]),
            "financial",
            _guard(finance_record_transaction),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_update_budget",
            "Replace a budget's category lines. Money write: always needs approval.",
            _obj(
                {
                    "budget_id": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": _obj(
                            {
                                "category_id": {"type": "string"},
                                "planned": _AMOUNT,
                                "alert_at_pct": {"type": "integer", "minimum": 1, "maximum": 100},
                            },
                            ["category_id", "planned"],
                        ),
                    },
                },
                ["budget_id", "lines"],
            ),
            "financial",
            _guard(finance_update_budget),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_change_recurring",
            "Change a recurring bill or income from its next occurrence. Needs approval.",
            _obj(
                {
                    "rule_id": {"type": "string"},
                    "title": {"type": "string"},
                    "amount": _AMOUNT,
                    "rule": _RULE,
                    "remind_days_before": {"type": "integer"},
                },
                ["rule_id"],
            ),
            "financial",
            _guard(finance_change_recurring),
            integration="finance",
        ),  # fmt: skip
        spec(
            "finance_delete_transaction",
            "Delete a transaction (recoverable for 30 days). Always needs approval.",
            _obj({"transaction_id": {"type": "string"}}, ["transaction_id"]),
            "destructive",
            _guard(finance_delete_transaction),
            integration="finance",
        ),  # fmt: skip
    ]
