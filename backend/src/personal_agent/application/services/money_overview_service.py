"""Money overview by period and payslips (Improvement Plan: personal finance module).

One switcher value drives every number: income, expense, net, change vs the previous equal
range, category shares, pace and daily allowance. All figures come from ledger rows; nothing is
estimated except the clearly labelled forecast for a range that has not started.
"""

from __future__ import annotations

import contextlib
import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from personal_agent.application.services.finance_service import (
    OPEN_OCC,
    SAVINGS_CATEGORIES,
    FinanceService,
)
from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.finance import DEFAULT_CURRENCY, month_bounds
from personal_agent.domain.finance_periods import (
    DEFAULT_PERIOD_START_DAY,
    INCOME_COMPONENTS,
    DateRange,
    Payslip,
    PayslipRepository,
    below_buffer,
    change_pct,
    comparison_range,
    compute_deductions,
    daily_allowance,
    days_left_in,
    default_split,
    elapsed_share,
    forecast_left,
    gross_pay,
    net_pay,
    pace,
    payroll_rules,
    period_range,
    resolve_range,
    share_pct,
    validate_payslip,
    variable_average,
)
from personal_agent.domain.life import LifeError, LifeNotFound

DEFAULT_BUFFER_MINOR = 200_000  # 2,000 ETB, a setting once Settings gets a money section
TOP_N = 5
PACE_WARN = 1.2
UNUSUAL_FACTOR = 3
UNUSUAL_MIN_HISTORY = 3
UNLOGGED_HOUR = 21


def formatted(minor: int) -> str:
    from personal_agent.domain.finance import format_money

    return format_money(minor)


def _csv_safe(value: str) -> str:
    """Stop spreadsheet formula injection from merchant/note text."""
    return "'" + value if value[:1] in ("=", "+", "-", "@") else value


def _minor(value: Any, name: str) -> int:
    """A major-unit amount ('1,500.50') to minor units; blank/zero means none."""
    if value in (None, "", 0, "0"):
        return 0
    from personal_agent.domain.finance import to_minor

    return to_minor(value, name)


def _major(minor: int) -> str:
    return f"{minor // 100}.{minor % 100:02d}"


class MoneyOverviewService:
    def __init__(
        self, finance: FinanceService, payslips: PayslipRepository, ctx: LifeContext
    ) -> None:
        self._fin = finance
        self._slips = payslips
        self._ctx = ctx

    # -- payslips --------------------------------------------------------------------------

    @staticmethod
    def payslip_payload(p: Payslip) -> dict[str, Any]:
        gross = p.gross_minor
        return {
            "id": p.id,
            "period_start": p.period_start.isoformat(),
            "period_end": p.period_end.isoformat(),
            "payday": p.payday.isoformat(),
            "components": p.components,
            "deductions": p.deductions,
            "gross_minor": gross,
            "net_minor": p.net_minor,
            "account_id": p.account_id,
            "transaction_id": p.transaction_id,
            # every line as a share of gross, like the payroll dashboard
            "shares": {
                **{k: share_pct(v, gross) for k, v in p.components.items()},
                **{f"deduction:{k}": share_pct(v, gross) for k, v in p.deductions.items()},
            },
        }

    @staticmethod
    def _payslip_inputs(
        data: dict[str, Any],
    ) -> tuple[date, dict[str, int], dict[str, int], DateRange]:
        allowed = {
            "payday",
            "components",
            "deductions",
            "account_id",
            "record_income",
            "period_start_day",
        }
        extra = set(data) - allowed
        if extra:
            raise LifeError(f"Unknown field: {sorted(extra)[0]}.")
        try:
            payday = date.fromisoformat(str(data.get("payday")))
        except ValueError:
            raise LifeError("payday must be a date like 2026-11-10.") from None
        components = {k: _minor(v, k) for k, v in (data.get("components") or {}).items()}
        typed = {k: _minor(v, k) for k, v in (data.get("deductions") or {}).items()}
        validate_payslip(components, typed)
        # Income tax and pension are calculated unless typed in (an override from a payslip).
        deductions = compute_deductions(components, typed)
        validate_payslip(components, deductions)
        start_day = int(data.get("period_start_day") or DEFAULT_PERIOD_START_DAY)
        # The pay period that contains the payday, e.g. 10 Nov to 9 Dec.
        rng = period_range(start_day, payday)
        return payday, components, deductions, rng

    def preview_payslip(self, owner: str, data: dict[str, Any]) -> dict[str, Any]:
        """Gross, tax, pension and net for the form, without saving anything."""
        del owner
        payday, components, deductions, rng = self._payslip_inputs(data)
        gross = gross_pay(components)
        slip = Payslip(
            "", "", rng.first, rng.last, payday, components, deductions,
            gross, net_pay(gross, deductions),
        )  # fmt: skip
        payload = self.payslip_payload(slip)
        payload["auto"] = sorted(
            k for k in ("income_tax", "pension") if k not in (data.get("deductions") or {})
        )
        payload["rules"] = payroll_rules()
        return payload

    def payroll_rules(self) -> dict[str, Any]:
        return dict(payroll_rules())

    def record_payslip(self, owner: str, data: dict[str, Any]) -> dict[str, Any]:
        """Save a payslip (amounts in major units) and log its net as income by default."""
        payday, components, deductions, rng = self._payslip_inputs(data)
        gross = gross_pay(components)
        net = net_pay(gross, deductions)
        slip = Payslip(
            uuid.uuid4().hex, owner, rng.first, rng.last, payday, components, deductions,
            gross, net, data.get("account_id") or None,
        )  # fmt: skip
        existing = next((p for p in self._slips.list(owner) if p.period_start == rng.first), None)
        record_income = data.get("record_income", True)
        if existing and existing.transaction_id:
            slip.transaction_id = existing.transaction_id
            # Keep the logged income in step with the corrected payslip.
            self._fin.update(
                owner,
                existing.transaction_id,
                {"amount": _major(net), "occurred_at": payday.isoformat()},
            )
        elif record_income:
            self._fin.ensure_setup(owner)
            salary = next(
                (c.id for c in self._fin._repo.list_categories(owner) if c.name == "Salary"),  # noqa: SLF001
                None,
            )
            txs = self._fin.record(
                owner,
                {
                    "kind": "income",
                    "amount": _major(net),
                    "occurred_at": payday.isoformat(),
                    "account_id": slip.account_id,
                    "category_id": salary,
                    "merchant": "Salary",
                    "note": f"Payslip {rng.first} to {rng.last}",
                },
            )
            slip.transaction_id = txs[0].id
        saved = self._slips.upsert(slip)
        self._ctx.record("finance.payslip", owner, id=saved.id, gross=gross, net=net)
        return self.payslip_payload(saved)

    def delete_payslip(self, owner: str, payslip_id: str) -> None:
        """Delete a payslip and the income it logged (if that income still exists)."""
        slip = self._slips.get(owner, payslip_id)
        if slip is None:
            raise not_found("Payslip")
        if slip.transaction_id:
            # The income row may already have been removed by hand.
            with contextlib.suppress(LifeNotFound):
                self._fin.delete(owner, slip.transaction_id)
        self._slips.delete(owner, payslip_id)
        self._ctx.record("finance.payslip_deleted", owner, id=payslip_id)

    def payslips(self, owner: str) -> list[dict[str, Any]]:
        items = list(self._slips.list(owner))
        out = []
        for index, slip in enumerate(items):
            payload = self.payslip_payload(slip)
            prior = items[index + 1] if index + 1 < len(items) else None
            payload["net_change_pct"] = (
                change_pct(slip.net_minor, prior.net_minor) if prior else None
            )
            out.append(payload)
        return out

    def payslip(self, owner: str, payslip_id: str) -> dict[str, Any]:
        slip = self._slips.get(owner, payslip_id)
        if slip is None:
            raise not_found("Payslip")
        return self.payslip_payload(slip)

    # -- overview --------------------------------------------------------------------------

    def _payday(self, owner: str) -> int | None:
        latest = self._slips.latest(owner)
        return min(latest.payday.day, 28) if latest else None

    def _ledger(self, owner: str, rng: DateRange) -> dict[str, Any]:
        """Totals and breakdowns for one range, from ledger rows only."""
        start, end = self._fin._range(owner, rng.first, rng.last)  # noqa: SLF001
        cats = {c.id: c for c in self._fin._repo.list_categories(owner)}  # noqa: SLF001
        income = spent = saved = 0
        income_by: dict[str, int] = defaultdict(int)
        spent_by: dict[str, int] = defaultdict(int)
        by_day: dict[str, int] = defaultdict(int)
        spends: list[dict[str, Any]] = []
        count = 0
        for tx in self._fin._repo.query_tx(owner, start=start, end=end, limit=100000):  # noqa: SLF001
            if tx.kind == "transfer":
                continue  # moving your own money is never income or expense
            count += 1
            cat = cats.get(tx.category_id or "")
            name = cat.name if cat else "Uncategorised"
            if tx.kind == "income":
                income += tx.amount_minor
                income_by[name] += tx.amount_minor
            elif name in SAVINGS_CATEGORIES:
                saved += tx.amount_minor
            else:
                spent += tx.amount_minor
                spent_by[name] += tx.amount_minor
                day = self._ctx.local_date(owner, tx.occurred_at).isoformat()
                by_day[day] += tx.amount_minor
                spends.append(
                    {"id": tx.id, "merchant": tx.merchant or name, "category": name,
                     "amount_minor": tx.amount_minor, "occurred_at": tx.occurred_at.isoformat()}
                )  # fmt: skip
        return {
            "income": income, "spent": spent, "saved": saved, "count": count,
            "income_by": dict(income_by), "spent_by": dict(spent_by), "by_day": dict(by_day),
            "spends": sorted(spends, key=lambda s: -s["amount_minor"])[:TOP_N],
        }  # fmt: skip

    def overview(
        self,
        owner: str,
        kind: str = "month",
        *,
        start: date | None = None,
        end: date | None = None,
    ) -> dict[str, Any]:
        self._fin.ensure_setup(owner)
        today = self._ctx.today(owner)
        payday = self._payday(owner)
        rng = resolve_range(kind, today, start=start, end=end, payday=payday)
        prev = comparison_range(kind, rng)
        cur = self._ledger(owner, rng)
        old = self._ledger(owner, prev)
        net = cur["income"] - cur["spent"] - cur["saved"]
        planned = self._planned(owner, rng)
        left_base = planned if planned else cur["income"]
        left = left_base - cur["spent"] - cur["saved"]
        share = elapsed_share(rng, today)
        days_left = days_left_in(rng, today)
        categories = [
            {
                "category": name,
                "amount_minor": amount,
                "share_pct": share_pct(amount, cur["spent"]),
                "previous_minor": old["spent_by"].get(name, 0),
                "change_pct": change_pct(amount, old["spent_by"].get(name, 0)),
            }
            for name, amount in sorted(cur["spent_by"].items(), key=lambda kv: -kv[1])
        ]
        days = []
        day = rng.first
        while day <= rng.last and rng.days <= 62:  # a daily bar chart past ~2 months is noise
            days.append(
                {"day": day.isoformat(), "spent_minor": cur["by_day"].get(day.isoformat(), 0)}
            )
            day += timedelta(days=1)
        payload: dict[str, Any] = {
            "range": kind,
            "first": rng.first.isoformat(),
            "last": rng.last.isoformat(),
            "previous": {"first": prev.first.isoformat(), "last": prev.last.isoformat()},
            "currency": DEFAULT_CURRENCY,
            "income_minor": cur["income"],
            "spent_minor": cur["spent"],
            "saved_minor": cur["saved"],
            "net_minor": net,
            "left_minor": left,
            "income_change_pct": change_pct(cur["income"], old["income"]),
            "spent_change_pct": change_pct(cur["spent"], old["spent"]),
            "saved_change_pct": change_pct(cur["saved"], old["saved"]),
            "net_change_pct": change_pct(net, old["income"] - old["spent"] - old["saved"])
            if old["income"] - old["spent"] - old["saved"] > 0
            else None,
            "budget_planned_minor": planned,
            "pace": pace(cur["spent"], planned, share) if planned else None,
            "daily_allowance_minor": daily_allowance(left, days_left)
            if rng.first <= today <= rng.last
            else None,
            "days_left": days_left,
            "savings_rate_pct": share_pct(cur["saved"], cur["income"]),
            "income_breakdown": [
                {"source": k, "amount_minor": v, "share_pct": share_pct(v, cur["income"])}
                for k, v in sorted(cur["income_by"].items(), key=lambda kv: -kv[1])
            ],
            "categories": categories,
            "top_categories": categories[:TOP_N],
            "biggest_spends": cur["spends"],
            "by_day": days,
            "transaction_count": cur["count"],
            "forecast": None,
        }
        if rng.first > today:
            payload["forecast"] = self.forecast(owner, rng)
        return payload

    def _planned(self, owner: str, rng: DateRange) -> int:
        for budget in self._fin._repo.list_budgets(owner):  # noqa: SLF001
            if budget.type == "monthly" and budget.period_start == rng.first:
                return sum(line.planned_minor for line in budget.lines)
        return 0

    def forecast(self, owner: str, rng: DateRange) -> dict[str, Any]:
        """Expected income - committed - variable - planned savings for a range not yet started."""
        latest = self._slips.latest(owner)
        income = latest.net_minor if latest else 0
        committed = 0
        for occ in self._fin.occurrences(owner, rng.first, rng.last):
            if occ["status"] not in OPEN_OCC:
                continue
            if occ["kind"] == "bill":
                committed += occ["remaining_minor"]
            elif occ["kind"] == "income":
                income += occ["remaining_minor"]
        history = []
        for back in (1, 2, 3):
            first, last = month_bounds(_shift_period(rng.first, -back))
            led = self._ledger(owner, DateRange(first, last))
            fixed = sum(v for k, v in led["spent_by"].items() if k in self._fixed_names(owner))
            history.append(led["spent"] - fixed)
        variable = variable_average(history)
        savings = sum(g["monthly_contribution_minor"] for g in self._fin.savings_goals(owner))
        left = forecast_left(income, committed, variable, savings)
        buffer = DEFAULT_BUFFER_MINOR
        trim = []
        if below_buffer(left, buffer):
            led = self._ledger(owner, DateRange(*month_bounds(_shift_period(rng.first, -1))))
            trim = [
                {"category": k, "amount_minor": v}
                for k, v in sorted(led["spent_by"].items(), key=lambda kv: -kv[1])
                if k not in self._fixed_names(owner)
            ][:3]
        return {
            "expected_income_minor": income,
            "committed_minor": committed,
            "variable_minor": variable,
            "planned_savings_minor": savings,
            "left_minor": left,
            "buffer_minor": buffer,
            "below_buffer": below_buffer(left, buffer),
            "trim_suggestions": trim,
            "basis": "Last payslip net, bills due, 3-month average variable spend.",
            "has_payslip": latest is not None,
        }

    def _fixed_names(self, owner: str) -> set[str]:
        return {c.name for c in self._fin._repo.list_categories(owner) if c.is_fixed}  # noqa: SLF001

    # -- alerts ----------------------------------------------------------------------------

    def alerts(self, owner: str) -> list[dict[str, Any]]:
        """Pace, unusual-spend and unlogged-day alerts (bills and budgets alert elsewhere)."""
        self._fin.ensure_setup(owner)
        today = self._ctx.today(owner)
        out: list[dict[str, Any]] = []
        month = self.overview(owner, "month")
        if month["pace"] is not None and month["pace"] > PACE_WARN and month["days_left"] > 7:
            out.append(
                {
                    "kind": "pace",
                    "severity": "warning",
                    "message": f"Spending is at {month['pace']:.1f}x the pace of your budget "
                    f"with {month['days_left']} days left.",
                }
            )
        start, end = self._fin._range(owner, today - timedelta(days=90), today)  # noqa: SLF001
        cats = {c.id: c.name for c in self._fin._repo.list_categories(owner)}  # noqa: SLF001
        history: dict[str, list[int]] = defaultdict(list)
        recent: list[Any] = []
        cutoff = today - timedelta(days=7)
        for tx in self._fin._repo.query_tx(
            owner, start=start, end=end, kind="expense", limit=100000
        ):  # noqa: SLF001
            if tx.category_id is None:
                continue
            if self._ctx.local_date(owner, tx.occurred_at) > cutoff:
                recent.append(tx)
            else:
                history[tx.category_id].append(tx.amount_minor)
        for tx in recent:
            past = history.get(tx.category_id or "", [])
            if len(past) >= UNUSUAL_MIN_HISTORY and tx.amount_minor > UNUSUAL_FACTOR * (
                sum(past) / len(past)
            ):
                out.append(
                    {
                        "kind": "unusual",
                        "severity": "info",
                        "message": f"{formatted(tx.amount_minor)} on "
                        f"{cats.get(tx.category_id or '', 'a category')} is over "
                        f"{UNUSUAL_FACTOR}x its usual spend.",
                        "transaction_id": tx.id,
                    }
                )
        now_local = self._ctx.now().astimezone(self._fin._zone(owner))  # noqa: SLF001
        if now_local.hour >= UNLOGGED_HOUR:
            today_view = self.overview(owner, "today")
            week = self.overview(owner, "week")
            if today_view["spent_minor"] == 0 and week["transaction_count"] > 0:
                out.append(
                    {
                        "kind": "unlogged",
                        "severity": "info",
                        "message": "No expense logged today. Anything to add?",
                    }
                )
        return out

    # -- month close -------------------------------------------------------------------------

    def close(self, owner: str, period: str | None = None) -> dict[str, Any]:
        """Read-only close report: totals, uncategorised rows, unspent budget, a summary.

        It never moves money. The rollover is a proposal the owner applies (money asks first).
        """
        self._fin.ensure_setup(owner)
        period, first, last = self._fin._month(owner, period)  # noqa: SLF001
        rng = DateRange(first, last)
        led = self._ledger(owner, rng)
        prev = self._ledger(owner, comparison_range("month", rng))
        start, end = self._fin._range(owner, first, last)  # noqa: SLF001
        uncategorised = [
            {"id": t.id, "merchant": t.merchant, "amount_minor": t.amount_minor}
            for t in self._fin._repo.query_tx(owner, start=start, end=end, limit=100000)  # noqa: SLF001
            if t.kind != "transfer" and t.category_id is None
        ]
        planned = self._planned(owner, rng)
        unspent = max(planned - led["spent"] - led["saved"], 0) if planned else 0
        top = sorted(led["spent_by"].items(), key=lambda kv: -kv[1])[:3]
        parts = [
            f"{period}: income {formatted(led['income'])}, spent {formatted(led['spent'])}, "
            f"saved {formatted(led['saved'])}."
        ]
        change = change_pct(led["spent"], prev["spent"])
        if change is not None:
            parts.append(
                f"Spending is {abs(change)}% {'up' if change > 0 else 'down'} on last month."
            )
        if top:
            parts.append("Biggest: " + ", ".join(f"{k} {formatted(v)}" for k, v in top) + ".")
        if unspent:
            parts.append(f"{formatted(unspent)} of budget was left unspent.")
        if uncategorised:
            parts.append(f"{len(uncategorised)} entries still need a category.")
        return {
            "period": period,
            "income_minor": led["income"],
            "spent_minor": led["spent"],
            "saved_minor": led["saved"],
            "net_minor": led["income"] - led["spent"] - led["saved"],
            "savings_rate_pct": share_pct(led["saved"], led["income"]),
            "uncategorised": uncategorised,
            "unspent_budget_minor": unspent,
            "rollover_proposal": {"to": "Savings", "amount_minor": unspent} if unspent else None,
            "top_categories": [{"category": k, "amount_minor": v} for k, v in top],
            "summary": " ".join(parts),
            "ready": last < self._ctx.today(owner) or self._ctx.today(owner) == last,
        }

    def export_csv(self, owner: str) -> str:
        """Every ledger row as CSV (transfers included, deleted rows excluded)."""
        import csv
        import io

        cats = {c.id: c.name for c in self._fin._repo.list_categories(owner)}  # noqa: SLF001
        accounts = {a.id: a.name for a in self._fin._repo.list_accounts(owner)}  # noqa: SLF001
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            ["date", "kind", "amount", "currency", "category", "account", "merchant", "note"]
        )
        for tx in self._fin._repo.query_tx(owner, limit=1_000_000):  # noqa: SLF001
            writer.writerow(
                [
                    tx.occurred_at.date().isoformat(),
                    tx.kind,
                    _major(tx.amount_minor),
                    tx.currency,
                    cats.get(tx.category_id or "", ""),
                    accounts.get(tx.account_id or "", ""),
                    _csv_safe(tx.merchant),
                    _csv_safe(tx.note),
                ]
            )
        return buf.getvalue()

    def suggested_budget(self, owner: str) -> dict[str, Any]:
        """Needs 50 / wants 30 / savings 20 of the latest net, to edit (never saved here)."""
        latest = self._slips.latest(owner)
        if latest is None:
            raise LifeError("Record a payslip first so the budget can start from your net pay.")
        return {"net_minor": latest.net_minor, "split": default_split(latest.net_minor)}


def _shift_period(anchor: date, months: int) -> str:
    index = anchor.year * 12 + anchor.month - 1 + months
    return f"{index // 12:04d}-{index % 12 + 1:02d}"


__all__ = ["INCOME_COMPONENTS", "MoneyOverviewService"]
