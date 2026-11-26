"""Period maths for the Money page (Improvement Plan: income and expense by period).

Pure functions only. One switcher value (`today`, `week`, `month`, `last_month`, `next_month`,
`year`, `custom`) resolves to a date range; every total is compared with the previous equal
range, and the payslip/forecast formulas live here so they can be unit tested without a database.
Amounts are integer minor units, like the rest of the finance domain.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Protocol

from personal_agent.domain.life import LifeError

RANGE_KINDS = ("today", "week", "month", "last_month", "next_month", "year", "custom")
MAX_CUSTOM_DAYS = 800

INCOME_COMPONENTS = ("basic", "allowance", "benefit", "incentive", "performance")
DEDUCTION_TYPES = ("income_tax", "pension", "loan", "other")
DEFAULT_SPLIT = (("needs", 50), ("wants", 30), ("savings", 20))


@dataclass(frozen=True, slots=True)
class DateRange:
    first: date
    last: date

    @property
    def days(self) -> int:
        return (self.last - self.first).days + 1


def _add_months(day: date, months: int) -> date:
    index = day.year * 12 + day.month - 1 + months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_range(day: date, offset: int = 0) -> DateRange:
    anchor = _add_months(day.replace(day=1), offset)
    return DateRange(anchor, anchor.replace(day=calendar.monthrange(anchor.year, anchor.month)[1]))


def period_range(payday: int, day: date, offset: int = 0) -> DateRange:
    """Payday-to-payday period containing `day` (e.g. payday 10 -> 10th to 9th)."""
    if not 1 <= payday <= 28:
        raise LifeError("payday must be between 1 and 28.")
    start = day.replace(day=payday)
    if day.day < payday:
        start = _add_months(start, -1)
    start = _add_months(start, offset)
    return DateRange(start, _add_months(start, 1) - timedelta(days=1))


def resolve_range(
    kind: str,
    today: date,
    *,
    week_starts_on: int = 0,
    start: date | None = None,
    end: date | None = None,
    payday: int | None = None,
) -> DateRange:
    """Resolve a switcher value to a range. `payday` turns month views into pay periods."""
    if kind not in RANGE_KINDS:
        raise LifeError(f"range must be one of: {', '.join(RANGE_KINDS)}.")
    if kind == "today":
        return DateRange(today, today)
    if kind == "week":
        first = today - timedelta(days=(today.weekday() - week_starts_on) % 7)
        return DateRange(first, first + timedelta(days=6))
    if kind in ("month", "last_month", "next_month"):
        offset = {"month": 0, "last_month": -1, "next_month": 1}[kind]
        return period_range(payday, today, offset) if payday else month_range(today, offset)
    if kind == "year":
        return DateRange(date(today.year, 1, 1), date(today.year, 12, 31))
    if start is None or end is None:
        raise LifeError("custom range needs start and end dates.")
    if end < start:
        raise LifeError("end must not be before start.")
    if (end - start).days + 1 > MAX_CUSTOM_DAYS:
        raise LifeError(f"custom range is limited to {MAX_CUSTOM_DAYS} days.")
    return DateRange(start, end)


def comparison_range(kind: str, current: DateRange) -> DateRange:
    """The range a total is compared with: the previous equal range (month -> previous month)."""
    if kind in ("month", "last_month", "next_month"):
        prev_last = current.first - timedelta(days=1)
        if current.days >= 28:  # calendar month or pay period: step one whole period back
            return DateRange(_add_months(current.first, -1), prev_last)
    if kind == "year":
        return DateRange(date(current.first.year - 1, 1, 1), date(current.first.year - 1, 12, 31))
    span = timedelta(days=current.days)
    return DateRange(current.first - span, current.last - span)


# -- figures -----------------------------------------------------------------------------


def change_pct(current: int, previous: int) -> float | None:
    """(this - last) / last as a percentage; None when there is nothing to compare with."""
    if previous <= 0:
        return None
    return round((current - previous) / previous * 100, 1)


def share_pct(part: int, total: int) -> float:
    return round(part / total * 100, 1) if total > 0 else 0.0


def elapsed_share(rng: DateRange, today: date) -> float:
    """Share of the range already elapsed (0..1)."""
    if today < rng.first:
        return 0.0
    if today >= rng.last:
        return 1.0
    return ((today - rng.first).days + 1) / rng.days


def pace(spent: int, budget: int, share_elapsed: float) -> float | None:
    """Spent so far / (budget x share elapsed). Above 1.0 means overspending."""
    if budget <= 0 or share_elapsed <= 0:
        return None
    return round(spent / (budget * share_elapsed), 2)


def daily_allowance(left: int, days_left: int) -> int:
    """Remaining free-to-spend divided by days left (today counts)."""
    return max(left, 0) // max(days_left, 1)


def days_left_in(rng: DateRange, today: date) -> int:
    if today > rng.last:
        return 0
    return (rng.last - max(today, rng.first)).days + 1


def gross_pay(components: Mapping[str, int]) -> int:
    """Gross = Basic + Allowances + Benefits + Incentive + Performance pay."""
    return sum(int(components.get(name, 0)) for name in INCOME_COMPONENTS)


def net_pay(gross: int, deductions: Mapping[str, int]) -> int:
    """Net = Gross - (income tax + pension + loans + other deductions)."""
    return gross - sum(int(deductions.get(name, 0)) for name in DEDUCTION_TYPES)


def validate_payslip(components: Mapping[str, int], deductions: Mapping[str, int]) -> None:
    for name, value in (*components.items(), *deductions.items()):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise LifeError(f"{name} must be a whole, non-negative amount.")
    unknown = set(components) - set(INCOME_COMPONENTS)
    if unknown:
        raise LifeError(f"Unknown income component: {sorted(unknown)[0]}.")
    unknown = set(deductions) - set(DEDUCTION_TYPES)
    if unknown:
        raise LifeError(f"Unknown deduction: {sorted(unknown)[0]}.")
    gross = gross_pay(components)
    if gross <= 0:
        raise LifeError("A payslip needs at least one income component above zero.")
    if net_pay(gross, deductions) < 0:
        raise LifeError("Deductions cannot be larger than gross pay.")


def pension_amount(basic: int, rate_pct: float) -> int:
    """Employee pension share from the basic salary; the rate is a setting, not hard-coded."""
    if not 0 <= rate_pct <= 100:
        raise LifeError("pension rate must be between 0 and 100.")
    return round(basic * rate_pct / 100)


# -- payroll rules (Ethiopian PAYE, as configured in the Selamnew payroll settings) --------

# (upper bound of taxable monthly income in birr, rate %, deduction in birr); None = no cap.
DEFAULT_TAX_BRACKETS: tuple[tuple[int | None, int, int], ...] = (
    (2_000, 0, 0),
    (4_000, 15, 300),
    (7_000, 20, 500),
    (10_000, 25, 850),
    (14_000, 30, 1_350),
    (None, 35, 2_050),
)
DEFAULT_PENSION_EMPLOYEE_PCT = 7.0
DEFAULT_PENSION_EMPLOYER_PCT = 11.0
DEFAULT_PERIOD_START_DAY = 10


def income_tax(
    taxable_minor: int,
    brackets: Sequence[tuple[int | None, int, int]] = DEFAULT_TAX_BRACKETS,
) -> int:
    """Monthly income tax in minor units: taxable x rate - deduction for the bracket it falls in.

    Brackets are in major units (birr); amounts in and out are minor units (cents).
    """
    if taxable_minor <= 0:
        return 0
    for upper, rate, deduction in brackets:
        if upper is None or taxable_minor <= upper * 100:
            return max(0, round(taxable_minor * rate / 100) - deduction * 100)
    return 0  # unreachable with a final open bracket


def compute_deductions(
    components: Mapping[str, int],
    given: Mapping[str, int],
    *,
    brackets: Sequence[tuple[int | None, int, int]] = DEFAULT_TAX_BRACKETS,
    pension_pct: float = DEFAULT_PENSION_EMPLOYEE_PCT,
) -> dict[str, int]:
    """Fill in income tax and employee pension when they were not typed in.

    Explicit values win (an override from a real payslip); missing ones are calculated:
    tax on gross taxable pay, pension as a share of basic salary.
    """
    out = {k: int(v) for k, v in given.items()}
    if "income_tax" not in out:
        out["income_tax"] = income_tax(gross_pay(components), brackets)
    if "pension" not in out:
        out["pension"] = pension_amount(int(components.get("basic", 0)), pension_pct)
    return out


def payroll_rules() -> dict[str, object]:
    """The rules the calculator uses, for display beside the form."""
    return {
        "tax_brackets": [
            {"up_to": upper, "rate_pct": rate, "deduction": deduction}
            for upper, rate, deduction in DEFAULT_TAX_BRACKETS
        ],
        "pension_employee_pct": DEFAULT_PENSION_EMPLOYEE_PCT,
        "pension_employer_pct": DEFAULT_PENSION_EMPLOYER_PCT,
        "period_start_day": DEFAULT_PERIOD_START_DAY,
    }


def free_to_spend(net: int, side_income: int, fixed_bills: int, savings_transfers: int) -> int:
    """Free to spend = Net + Side income - Fixed bills - Savings transfers."""
    return net + side_income - fixed_bills - savings_transfers


def forecast_left(expected_income: int, committed: int, variable: int, planned_savings: int) -> int:
    """Forecast left = expected income - committed - variable - planned savings."""
    return expected_income - committed - variable - planned_savings


def variable_average(history: Sequence[int]) -> int:
    """Average of the periods that had any spend (a month with no data must not drag it to 0)."""
    values = [v for v in history if v > 0]
    return sum(values) // len(values) if values else 0


def below_buffer(forecast: int, buffer: int) -> bool:
    return forecast < buffer


def default_split(net: int) -> dict[str, int]:
    """Needs 50 / wants 30 / savings 20 of net, as a starting point to edit."""
    out = {name: net * pct // 100 for name, pct in DEFAULT_SPLIT}
    out["savings"] += net - sum(out.values())  # remainder goes to savings, never lost
    return out


@dataclass(slots=True)
class Payslip:
    id: str
    owner_user_id: str
    period_start: date
    period_end: date
    payday: date
    components: dict[str, int] = field(default_factory=dict)
    deductions: dict[str, int] = field(default_factory=dict)
    gross_minor: int = 0
    net_minor: int = 0
    account_id: str | None = None
    transaction_id: str | None = None


class PayslipRepository(Protocol):
    def upsert(self, payslip: Payslip) -> Payslip: ...
    def list(self, owner: str, *, limit: int = 24) -> Sequence[Payslip]: ...
    def latest(self, owner: str) -> Payslip | None: ...
    def get(self, owner: str, payslip_id: str) -> Payslip | None: ...
