"""Personal finance (section 6): a ledger of real transactions plus a schedule of expected ones.

Amounts are integers in the smallest unit (santim for ETB) with a currency code. Direction comes
from `kind`; `amount_minor` is always positive. Expected items (salary due, rent due) become
transactions only when the owner confirms them.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Protocol

from personal_agent.domain.life import LifeError
from personal_agent.domain.recurrence import RecurrenceRule

DEFAULT_CURRENCY = "ETB"
MINOR = 100
AMOUNT_MAX = 10**13

ACCOUNT_TYPES = ("cash", "bank", "mobile_money", "card")
TX_KINDS = ("income", "expense", "transfer")
TX_STATUSES = ("received", "paid", "partial")
OCC_STATUSES = ("expected", "paid", "partial", "overdue", "skipped")
RULE_KINDS = ("income", "bill")
BUDGET_TYPES = ("monthly", "weekly", "category", "project", "savings", "emergency", "special")
ALERT_DEFAULT_PCT = 80

# Seeded on first use: the owner's expense categories plus income sources.
DEFAULT_EXPENSE_CATEGORIES = (
    "Rent",
    "Household & Food",
    "Transport",
    "Internet & Mobile",
    "Personal",
    "Learning",
    "Health",
    "Family & Gifts",
    "Entertainment",
    "Church & Giving",
    "Clothing",
    "Utilities",
    "Savings",
    "Emergency",
)
DEFAULT_INCOME_CATEGORIES = ("Salary", "Freelance", "Gift", "Other income")
FIXED_CATEGORIES = frozenset({"Rent", "Internet & Mobile", "Utilities", "Savings", "Emergency"})


@dataclass(slots=True)
class Account:
    id: str
    owner_user_id: str
    name: str
    type: str = "cash"
    currency: str = DEFAULT_CURRENCY
    opening_balance_minor: int = 0
    archived: bool = False


@dataclass(slots=True)
class Category:
    id: str
    owner_user_id: str
    name: str
    kind: str  # income | expense
    parent_id: str | None = None
    icon: str = ""
    is_fixed: bool = False


@dataclass(slots=True)
class Transaction:
    id: str
    owner_user_id: str
    kind: str
    amount_minor: int
    currency: str
    occurred_at: datetime
    account_id: str | None = None
    category_id: str | None = None
    status: str = "paid"
    merchant: str = ""
    note: str = ""
    budget_id: str | None = None
    project_id: str | None = None
    occurrence_id: str | None = None
    transfer_group: str | None = None
    receipt_file_id: str | None = None
    created_by: str = "user"
    approval_id: str | None = None
    deleted_at: datetime | None = None
    created_at: datetime | None = None


@dataclass(slots=True)
class RecurringRule:
    id: str
    owner_user_id: str
    kind: str  # income | bill
    title: str
    amount_minor: int
    rule: RecurrenceRule
    category_id: str | None = None
    account_id: str | None = None
    remind_days_before: int = 3
    version: int = 1
    active: bool = True
    group_id: str = ""  # shared by every version of one logical rule
    effective_from: date | None = None
    effective_to: date | None = None  # set when a newer version supersedes this one


@dataclass(slots=True)
class Occurrence:
    id: str
    owner_user_id: str
    rule_id: str
    rule_version: int
    due_date: date
    expected_minor: int
    status: str = "expected"
    paid_minor: int = 0
    transaction_id: str | None = None


@dataclass(slots=True)
class Budget:
    id: str
    owner_user_id: str
    name: str
    type: str
    period_start: date
    period_end: date
    income_plan_minor: int = 0
    rollover: bool = False
    lines: list[BudgetLine] = field(default_factory=list)


@dataclass(slots=True)
class BudgetLine:
    category_id: str
    planned_minor: int
    alert_at_pct: int = ALERT_DEFAULT_PCT


@dataclass(slots=True)
class SavingsGoal:
    id: str
    owner_user_id: str
    name: str
    target_minor: int
    goal_id: str | None = None
    target_date: date | None = None
    monthly_contribution_minor: int = 0
    account_id: str | None = None
    currency: str = DEFAULT_CURRENCY


@dataclass(slots=True)
class Contribution:
    id: str
    savings_goal_id: str
    transaction_id: str | None
    amount_minor: int
    contributed_on: date


class FinanceRepository(Protocol):
    """Persistence port; implemented in infrastructure/persistence/finance_store.py."""

    # accounts / categories
    def list_accounts(self, owner: str) -> Sequence[Account]: ...
    def add_account(self, account: Account) -> None: ...
    def get_account(self, owner: str, account_id: str) -> Account | None: ...
    def list_categories(self, owner: str) -> Sequence[Category]: ...
    def add_category(self, category: Category) -> None: ...
    def get_category(self, owner: str, category_id: str) -> Category | None: ...
    # transactions
    def add_tx(self, tx: Transaction) -> None: ...
    def get_tx(self, owner: str, tx_id: str) -> Transaction | None: ...
    def save_tx(self, tx: Transaction) -> None: ...
    def query_tx(
        self,
        owner: str,
        *,
        start: datetime | None = None,
        end: datetime | None = None,
        category_id: str | None = None,
        account_id: str | None = None,
        kind: str | None = None,
        text: str = "",
        limit: int = 200,
        offset: int = 0,
    ) -> Sequence[Transaction]: ...
    # recurring
    def add_rule(self, rule: RecurringRule) -> None: ...
    def get_rule(self, owner: str, rule_id: str) -> RecurringRule | None: ...
    def save_rule(self, rule: RecurringRule) -> None: ...
    def list_rules(self, owner: str, *, active_only: bool = True) -> Sequence[RecurringRule]: ...
    def add_occurrence(self, occ: Occurrence) -> bool: ...
    def get_occurrence(self, owner: str, occ_id: str) -> Occurrence | None: ...
    def save_occurrence(self, occ: Occurrence) -> None: ...
    def list_occurrences(self, owner: str, *, start: date, end: date) -> Sequence[Occurrence]: ...
    def occurrence_dates(self, rule_id: str) -> set[date]: ...
    def delete_future_open_occurrences(self, rule_id: str, from_day: date) -> int: ...
    # budgets
    def add_budget(self, budget: Budget) -> None: ...
    def get_budget(self, owner: str, budget_id: str) -> Budget | None: ...
    def save_budget(self, budget: Budget) -> None: ...
    def list_budgets(self, owner: str) -> Sequence[Budget]: ...
    # savings
    def add_savings_goal(self, goal: SavingsGoal) -> None: ...
    def get_savings_goal(self, owner: str, goal_id: str) -> SavingsGoal | None: ...
    def list_savings_goals(self, owner: str) -> Sequence[SavingsGoal]: ...
    def add_contribution(self, contribution: Contribution) -> None: ...
    def list_contributions(self, goal_id: str) -> Sequence[Contribution]: ...


# -- money ---------------------------------------------------------------------------------


def to_minor(value: Any, field_name: str = "amount") -> int:
    """Parse a decimal amount ('250', '1,250.50') or an int of minor units' major value."""
    if isinstance(value, bool):
        raise LifeError(f"{field_name} must be a number.")
    if isinstance(value, int | float):
        text = repr(value)
    else:
        text = str(value or "").strip().replace(",", "").replace(" ", "")
    if not re.fullmatch(r"\d+(\.\d{1,2})?", text):
        raise LifeError(f"{field_name} must be a positive amount with at most 2 decimals.")
    whole, _, frac = text.partition(".")
    minor = int(whole) * MINOR + int((frac + "00")[:2])
    if minor <= 0:
        raise LifeError(f"{field_name} must be greater than zero.")
    if minor > AMOUNT_MAX:
        raise LifeError(f"{field_name} is too large.")
    return minor


def format_money(minor: int, currency: str = DEFAULT_CURRENCY) -> str:
    sign = "-" if minor < 0 else ""
    major, cents = divmod(abs(minor), MINOR)
    body = f"{major:,}" + (f".{cents:02d}" if cents else "")
    return f"{sign}{body} {currency}"


def clean_currency(value: Any) -> str:
    code = str(value or DEFAULT_CURRENCY).strip().upper()
    if not re.fullmatch(r"[A-Z]{3}", code):
        raise LifeError("currency must be a 3-letter code such as ETB.")
    return code


def clean_text(value: Any, name: str, limit: int, *, required: bool = False) -> str:
    text = str(value or "").strip()
    if required and not text:
        raise LifeError(f"{name} is required.")
    if len(text) > limit:
        raise LifeError(f"{name} must be at most {limit} characters.")
    return text


def month_bounds(period: str) -> tuple[date, date]:
    """'2026-11' -> (first, last) day of that month."""
    import calendar

    try:
        year_s, month_s = period.split("-")
        year, month = int(year_s), int(month_s)
        first = date(year, month, 1)
    except (ValueError, AttributeError) as exc:
        raise LifeError("period must look like 2026-11.") from exc
    return first, date(year, month, calendar.monthrange(year, month)[1])


# -- calculations (section 6.5) ----------------------------------------------------------


def utilisation_pct(actual: int, planned: int) -> float:
    return round(actual / planned * 100, 1) if planned > 0 else (100.0 if actual > 0 else 0.0)


def budget_status(actual: int, planned: int, alert_pct: int = ALERT_DEFAULT_PCT) -> str:
    """green under alert%, amber from alert% to 100%, red over 100%."""
    pct = utilisation_pct(actual, planned)
    if pct > 100:
        return "red"
    if pct >= alert_pct:
        return "amber"
    return "green"


def savings_rate_pct(income: int, non_savings_expenses: int) -> float:
    return round((income - non_savings_expenses) / income * 100, 1) if income > 0 else 0.0


def expected_end_balance(
    balance_now: int,
    expected_income: int,
    unpaid_bills: int,
    avg_daily_variable_spend: int,
    days_left: int,
) -> int:
    return (
        balance_now + expected_income - unpaid_bills - avg_daily_variable_spend * max(days_left, 0)
    )


def projected_completion(goal: SavingsGoal, saved_minor: int, today: date) -> date | None:
    """Date the goal completes at the planned monthly contribution (None when unknown)."""
    import calendar

    remaining = goal.target_minor - saved_minor
    if remaining <= 0:
        return today
    if goal.monthly_contribution_minor <= 0:
        return None
    months = -(-remaining // goal.monthly_contribution_minor)
    index = today.year * 12 + today.month - 1 + months
    year, month = index // 12, index % 12 + 1
    return date(year, month, min(today.day, calendar.monthrange(year, month)[1]))


# -- natural-language capture (never saves) -----------------------------------------------

_INCOME_WORDS = ("salary", "income", "received", "earned", "paid me", "bonus")
_AMOUNT_RE = re.compile(r"(?<![\w.])(\d[\d,]*(?:\.\d{1,2})?)(?![\w])")
_METHODS = {"cash": "cash", "telebirr": "mobile_money", "cbe": "bank", "card": "card"}


def parse_quick_text(text: str, categories: Sequence[Category]) -> dict[str, Any]:
    """'lunch 250 cash at Kaldi's' -> draft fields. Raises LifeError when no amount is found."""
    raw = (text or "").strip()
    if not raw:
        raise LifeError("Write something like 'lunch 250 cash'.")
    match = _AMOUNT_RE.search(raw)
    if match is None:
        raise LifeError("No amount found. Write something like 'lunch 250 cash'.")
    amount = to_minor(match.group(1))
    lowered = raw.lower()
    kind = "income" if any(w in lowered for w in _INCOME_WORDS) else "expense"
    merchant = ""
    at = re.search(r"\bat\s+([^\d,]+?)(?:\s+\d|$)", raw, flags=re.IGNORECASE)
    if at:
        merchant = at.group(1).strip(" .'\"")[:120]
    method = next((m for word, m in _METHODS.items() if re.search(rf"\b{word}\b", lowered)), None)
    category_id = None
    for category in categories:
        if category.kind == kind and category.name.lower().split(" &")[0] in lowered:
            category_id = category.id
            break
    note = re.sub(_AMOUNT_RE, "", raw, count=1).strip(" ,.")[:200]
    return {
        "kind": kind,
        "amount_minor": amount,
        "merchant": merchant,
        "category_id": category_id,
        "payment_method": method,
        "note": note,
    }


def validate_status(status: str, allowed: Sequence[str], name: str = "status") -> str:
    if status not in allowed:
        raise LifeError(f"{name} must be one of: {', '.join(allowed)}.")
    return status


def tx_payload(tx: Transaction) -> Mapping[str, Any]:
    return {
        "id": tx.id,
        "kind": tx.kind,
        "amount_minor": tx.amount_minor,
        "currency": tx.currency,
        "occurred_at": tx.occurred_at.isoformat(),
        "account_id": tx.account_id,
        "category_id": tx.category_id,
        "status": tx.status,
        "merchant": tx.merchant,
        "note": tx.note,
        "budget_id": tx.budget_id,
        "project_id": tx.project_id,
        "occurrence_id": tx.occurrence_id,
        "created_by": tx.created_by,
        "approval_id": tx.approval_id,
    }
