"""Personal finance service (section 6): ledger, recurring schedule, budgets, savings, summary."""

from __future__ import annotations

import contextlib
import uuid
from collections import defaultdict
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time, timedelta
from typing import Any

from personal_agent.application.services.life_common import LifeContext, not_found
from personal_agent.domain.dates import get_zone
from personal_agent.domain.finance import (
    ACCOUNT_TYPES,
    ALERT_DEFAULT_PCT,
    BUDGET_TYPES,
    DEFAULT_CURRENCY,
    DEFAULT_EXPENSE_CATEGORIES,
    DEFAULT_INCOME_CATEGORIES,
    FIXED_CATEGORIES,
    RULE_KINDS,
    TX_KINDS,
    Account,
    Budget,
    BudgetLine,
    Category,
    Contribution,
    FinanceRepository,
    Occurrence,
    RecurringRule,
    SavingsGoal,
    Transaction,
    budget_status,
    clean_currency,
    clean_text,
    expected_end_balance,
    format_money,
    month_bounds,
    parse_quick_text,
    projected_completion,
    savings_rate_pct,
    to_minor,
    tx_payload,
    utilisation_pct,
)
from personal_agent.domain.life import LifeConflict, LifeError
from personal_agent.domain.recurrence import RecurrenceError, iter_occurrences, parse_rule

HORIZON_DAYS = 90
BACKFILL_DAYS = 31
SAVINGS_CATEGORIES = frozenset({"Savings", "Emergency"})
OPEN_OCC = ("expected", "partial", "overdue")
UNKNOWN = "__unknown__"


_SEED_ORDER = {
    name: index
    for index, name in enumerate((*DEFAULT_EXPENSE_CATEGORIES, *DEFAULT_INCOME_CATEGORIES))
}


def _category_order(category: Category) -> tuple[str, int, str]:
    """Stable order: seeded categories as listed, then the owner's own, so chips never reshuffle."""
    return (category.kind, _SEED_ORDER.get(category.name, len(_SEED_ORDER)), category.name)


def _new_id() -> str:
    return uuid.uuid4().hex


def _only(data: Mapping[str, Any], allowed: set[str]) -> None:
    unknown = set(data) - allowed
    if unknown:
        raise LifeError(f"Unknown field(s): {', '.join(sorted(unknown))}.")


class FinanceService:
    def __init__(self, repository: FinanceRepository, ctx: LifeContext) -> None:
        self._repo = repository
        self._ctx = ctx

    # -- setup -----------------------------------------------------------------------------

    def ensure_setup(self, owner: str) -> None:
        """Seed the default categories and a cash wallet the first time finance is used."""
        if not self._repo.list_categories(owner):
            for name in DEFAULT_EXPENSE_CATEGORIES:
                self._safe_category(owner, name, "expense")
            for name in DEFAULT_INCOME_CATEGORIES:
                self._safe_category(owner, name, "income")
        if not self._repo.list_accounts(owner):
            self._repo.add_account(Account(_new_id(), owner, "Cash wallet", "cash"))

    def _safe_category(self, owner: str, name: str, kind: str) -> None:
        with contextlib.suppress(LifeConflict):
            self._repo.add_category(
                Category(_new_id(), owner, name, kind, is_fixed=name in FIXED_CATEGORIES)
            )

    def accounts(self, owner: str) -> list[dict[str, Any]]:
        self.ensure_setup(owner)
        balances = self.balances(owner)
        return [
            {
                "id": a.id,
                "name": a.name,
                "type": a.type,
                "currency": a.currency,
                "opening_balance_minor": a.opening_balance_minor,
                "balance_minor": balances.get(a.id, a.opening_balance_minor),
                "archived": a.archived,
            }
            for a in self._repo.list_accounts(owner)
        ]

    def create_account(self, owner: str, data: Mapping[str, Any]) -> Account:
        _only(data, {"name", "type", "currency", "opening_balance"})
        kind = str(data.get("type") or "cash")
        if kind not in ACCOUNT_TYPES:
            raise LifeError(f"type must be one of: {', '.join(ACCOUNT_TYPES)}.")
        opening = data.get("opening_balance")
        account = Account(
            _new_id(),
            owner,
            clean_text(data.get("name"), "name", 80, required=True),
            kind,
            clean_currency(data.get("currency")),
            to_minor(opening, "opening_balance") if opening not in (None, "", 0) else 0,
        )
        self._repo.add_account(account)
        self._ctx.record("finance.account_created", owner, account_id=account.id)
        return account

    def categories(self, owner: str) -> list[dict[str, Any]]:
        self.ensure_setup(owner)
        return [
            {
                "id": c.id,
                "name": c.name,
                "kind": c.kind,
                "parent_id": c.parent_id,
                "is_fixed": c.is_fixed,
            }
            for c in sorted(self._repo.list_categories(owner), key=_category_order)
        ]

    def create_category(self, owner: str, data: Mapping[str, Any]) -> Category:
        _only(data, {"name", "kind", "parent_id", "icon", "is_fixed"})
        kind = str(data.get("kind") or "expense")
        if kind not in ("income", "expense"):
            raise LifeError("kind must be income or expense.")
        parent_id = data.get("parent_id") or None
        if parent_id and self._repo.get_category(owner, str(parent_id)) is None:
            raise not_found("Parent category")
        category = Category(
            _new_id(),
            owner,
            clean_text(data.get("name"), "name", 80, required=True),
            kind,
            parent_id,
            clean_text(data.get("icon"), "icon", 16),
            bool(data.get("is_fixed", False)),
        )
        self._repo.add_category(category)
        return category

    # -- time helpers ----------------------------------------------------------------------

    def _zone(self, owner: str):
        return get_zone(self._ctx._profiles.timezone_for(owner))  # noqa: SLF001

    def _day_start(self, owner: str, day: date) -> datetime:
        return datetime.combine(day, time.min, tzinfo=self._zone(owner)).astimezone(UTC)

    def _range(self, owner: str, first: date, last: date) -> tuple[datetime, datetime]:
        return self._day_start(owner, first), self._day_start(owner, last + timedelta(days=1))

    def _parse_when(self, owner: str, value: Any) -> datetime:
        if value in (None, ""):
            return self._ctx.now()
        try:
            moment = datetime.fromisoformat(str(value))
        except ValueError as exc:
            raise LifeError("occurred_at must be an ISO date or date-time.") from exc
        if moment.tzinfo is None:
            if len(str(value)) <= 10:
                moment = datetime.combine(moment.date(), time(12, 0))
            moment = moment.replace(tzinfo=self._zone(owner))
        return moment.astimezone(UTC)

    # -- transactions ----------------------------------------------------------------------

    def _default_account(self, owner: str) -> Account:
        self.ensure_setup(owner)
        accounts = [a for a in self._repo.list_accounts(owner) if not a.archived]
        if not accounts:
            raise LifeError("Create an account first.")
        return accounts[0]

    def _check_refs(self, owner: str, account_id: Any, category_id: Any, kind: str) -> None:
        if account_id and self._repo.get_account(owner, str(account_id)) is None:
            raise not_found("Account")
        if category_id:
            category = self._repo.get_category(owner, str(category_id))
            if category is None:
                raise not_found("Category")
            if kind in ("income", "expense") and category.kind != kind:
                raise LifeError(f"That category is for {category.kind}, not {kind}.")

    _TX_FIELDS = {
        "kind",
        "amount",
        "occurred_at",
        "account_id",
        "to_account_id",
        "category_id",
        "merchant",
        "note",
        "budget_id",
        "project_id",
        "status",
        "receipt_file_id",
    }

    def record(
        self,
        owner: str,
        data: Mapping[str, Any],
        *,
        created_by: str = "user",
        approval_id: str | None = None,
        occurrence_id: str | None = None,
    ) -> list[Transaction]:
        """Create one transaction (two linked rows for a transfer)."""
        _only(data, self._TX_FIELDS)
        kind = str(data.get("kind") or "expense")
        if kind not in TX_KINDS:
            raise LifeError(f"kind must be one of: {', '.join(TX_KINDS)}.")
        amount = to_minor(data.get("amount"))
        account = (
            self._repo.get_account(owner, str(data["account_id"]))
            if data.get("account_id")
            else self._default_account(owner)
        )
        if account is None:
            raise not_found("Account")
        self._check_refs(owner, None, data.get("category_id"), kind)
        when = self._parse_when(owner, data.get("occurred_at"))
        base: dict[str, Any] = {
            "owner_user_id": owner,
            "amount_minor": amount,
            "currency": account.currency,
            "occurred_at": when,
            "merchant": clean_text(data.get("merchant"), "merchant", 120),
            "note": clean_text(data.get("note"), "note", 500),
            "budget_id": data.get("budget_id") or None,
            "project_id": data.get("project_id") or None,
            "occurrence_id": occurrence_id,
            "receipt_file_id": data.get("receipt_file_id") or None,
            "created_by": created_by,
            "approval_id": approval_id,
            "created_at": self._ctx.now(),
        }
        if kind == "transfer":
            target = self._repo.get_account(owner, str(data.get("to_account_id") or ""))
            if target is None:
                raise LifeError("A transfer needs to_account_id.")
            if target.id == account.id:
                raise LifeError("A transfer needs two different accounts.")
            if target.currency != account.currency:
                raise LifeError("Transfers between currencies are not supported.")
            group = _new_id()
            out = Transaction(
                id=_new_id(), kind="transfer", status="paid", account_id=account.id,
                category_id=data.get("category_id") or None, transfer_group=group, **base,
            )  # fmt: skip
            into = Transaction(
                id=_new_id(), kind="transfer", status="received", account_id=target.id,
                category_id=data.get("category_id") or None, transfer_group=group, **base,
            )  # fmt: skip
            self._repo.add_tx(out)
            self._repo.add_tx(into)
            self._ctx.record("finance.transfer", owner, transfer_group=group, created_by=created_by)
            return [out, into]
        status = str(data.get("status") or ("received" if kind == "income" else "paid"))
        if status not in ("received", "paid", "partial"):
            raise LifeError("status must be received, paid or partial.")
        tx = Transaction(
            id=_new_id(),
            kind=kind,
            status=status,
            account_id=account.id,
            category_id=data.get("category_id") or None,
            **base,
        )
        self._repo.add_tx(tx)
        self._ctx.record(
            "finance.recorded", owner, tx_id=tx.id, kind=kind, created_by=created_by,
            approval_id=approval_id,
        )  # fmt: skip
        return [tx]

    def quick(self, owner: str, amount: Any, category_id: str | None = None) -> Transaction:
        """Expense in one step: amount + category; everything else defaulted."""
        return self.record(
            owner, {"kind": "expense", "amount": amount, "category_id": category_id}
        )[0]

    def get(self, owner: str, tx_id: str) -> Transaction:
        tx = self._repo.get_tx(owner, tx_id)
        if tx is None or tx.deleted_at is not None:
            raise not_found("Transaction")
        return tx

    def update(self, owner: str, tx_id: str, data: Mapping[str, Any]) -> Transaction:
        _only(data, self._TX_FIELDS - {"kind", "to_account_id"})
        tx = self.get(owner, tx_id)
        if tx.kind == "transfer":
            raise LifeError("Delete and re-create a transfer to change it.")
        if "amount" in data:
            tx.amount_minor = to_minor(data["amount"])
        if "occurred_at" in data:
            tx.occurred_at = self._parse_when(owner, data["occurred_at"])
        if "account_id" in data:
            account = self._repo.get_account(owner, str(data["account_id"] or ""))
            if account is None:
                raise not_found("Account")
            tx.account_id, tx.currency = account.id, account.currency
        if "category_id" in data:
            self._check_refs(owner, None, data["category_id"], tx.kind)
            tx.category_id = data["category_id"] or None
        for name, limit in (("merchant", 120), ("note", 500)):
            if name in data:
                setattr(tx, name, clean_text(data[name], name, limit))
        for name in ("budget_id", "project_id", "receipt_file_id"):
            if name in data:
                setattr(tx, name, data[name] or None)
        if "status" in data:
            if data["status"] not in ("received", "paid", "partial"):
                raise LifeError("status must be received, paid or partial.")
            tx.status = data["status"]
        self._repo.save_tx(tx)
        self._ctx.record("finance.updated", owner, tx_id=tx.id)
        return tx

    def delete(self, owner: str, tx_id: str) -> int:
        """Soft delete (30-day recoverable); a transfer removes both legs."""
        tx = self.get(owner, tx_id)
        removed = 0
        legs = [tx]
        if tx.transfer_group:
            legs = [
                t
                for t in self._repo.query_tx(owner, kind="transfer", limit=1000)
                if t.transfer_group == tx.transfer_group
            ]
        now = self._ctx.now()
        for leg in legs:
            leg.deleted_at = now
            self._repo.save_tx(leg)
            removed += 1
        self._ctx.record("finance.deleted", owner, tx_id=tx.id, legs=removed)
        return removed

    def transactions(
        self,
        owner: str,
        *,
        period: str | None = None,
        category_id: str | None = None,
        account_id: str | None = None,
        kind: str | None = None,
        text: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[Transaction]:
        start = end = None
        if period:
            first, last = month_bounds(period)
            start, end = self._range(owner, first, last)
        return list(
            self._repo.query_tx(
                owner, start=start, end=end, category_id=category_id, account_id=account_id,
                kind=kind, text=text, limit=max(1, min(limit, 500)), offset=max(0, offset),
            )
        )  # fmt: skip

    def parse(self, owner: str, text: str) -> dict[str, Any]:
        """Natural-language text -> draft. Never saves."""
        self.ensure_setup(owner)
        draft = parse_quick_text(text, self._repo.list_categories(owner))
        method = draft.pop("payment_method", None)
        account = None
        if method:
            account = next((a for a in self._repo.list_accounts(owner) if a.type == method), None)
        draft["account_id"] = account.id if account else None
        draft["currency"] = account.currency if account else DEFAULT_CURRENCY
        return {"draft": draft, "saved": False}

    def balances(self, owner: str) -> dict[str, int]:
        result = {a.id: a.opening_balance_minor for a in self._repo.list_accounts(owner)}
        for tx in self._repo.query_tx(owner, limit=100000):
            if tx.account_id is None:
                continue
            plus = tx.kind == "income" or (tx.kind == "transfer" and tx.status == "received")
            result[tx.account_id] = result.get(tx.account_id, 0) + (
                tx.amount_minor if plus else -tx.amount_minor
            )
        return result

    # -- recurring rules and occurrences -------------------------------------------------

    _RULE_FIELDS = {"kind", "title", "amount", "category_id", "account_id", "rule",
                    "remind_days_before"}  # fmt: skip

    def _rule_obj(self, raw: Any, default_start: date):
        if not isinstance(raw, Mapping):
            raise LifeError("rule is required (freq, start, ...).")
        try:
            return parse_rule(dict(raw), default_start=default_start)
        except RecurrenceError as exc:
            raise LifeError(str(exc)) from exc

    def create_recurring(self, owner: str, data: Mapping[str, Any]) -> RecurringRule:
        _only(data, self._RULE_FIELDS)
        kind = str(data.get("kind") or "bill")
        if kind not in RULE_KINDS:
            raise LifeError(f"kind must be one of: {', '.join(RULE_KINDS)}.")
        self._check_refs(owner, data.get("account_id"), data.get("category_id"),
                         "income" if kind == "income" else "expense")  # fmt: skip
        today = self._ctx.today(owner)
        rule = RecurringRule(
            id=_new_id(),
            owner_user_id=owner,
            kind=kind,
            title=clean_text(data.get("title"), "title", 120, required=True),
            amount_minor=to_minor(data.get("amount")),
            rule=self._rule_obj(data.get("rule"), today),
            category_id=data.get("category_id") or None,
            account_id=data.get("account_id") or None,
            remind_days_before=self._remind(data.get("remind_days_before", 3)),
        )
        rule.group_id = rule.id
        rule.effective_from = rule.rule.start
        self._repo.add_rule(rule)
        self.generate_occurrences(owner)
        self._ctx.record("finance.rule_created", owner, rule_id=rule.id)
        return rule

    @staticmethod
    def _remind(value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 30:
            raise LifeError("remind_days_before must be 0 to 30.")
        return value

    def change_recurring(
        self, owner: str, rule_id: str, data: Mapping[str, Any], *, approval_id: str | None = None
    ) -> RecurringRule:
        """Edit = new version from the next occurrence; history is never rewritten."""
        _only(data, self._RULE_FIELDS - {"kind"})
        old = self._repo.get_rule(owner, rule_id)
        if old is None or not old.active:
            raise not_found("Recurring rule")
        today = self._ctx.today(owner)
        if "category_id" in data or "account_id" in data:
            self._check_refs(
                owner, data.get("account_id"), data.get("category_id"),
                "income" if old.kind == "income" else "expense",
            )  # fmt: skip
        raw_rule = data.get("rule")
        new_rule = old.rule
        if raw_rule is not None:
            new_rule = self._rule_obj(
                {**old.rule.to_dict(), **dict(raw_rule), "start": today.isoformat()}, today
            )
        upcoming = next(iter_occurrences(old.rule, today, today + timedelta(days=366)), today)
        version = RecurringRule(
            id=_new_id(),
            owner_user_id=owner,
            kind=old.kind,
            title=clean_text(data.get("title", old.title), "title", 120, required=True),
            amount_minor=to_minor(data["amount"]) if "amount" in data else old.amount_minor,
            rule=new_rule,
            category_id=data.get("category_id", old.category_id) or None,
            account_id=data.get("account_id", old.account_id) or None,
            remind_days_before=self._remind(data.get("remind_days_before", old.remind_days_before)),
            version=old.version + 1,
            group_id=old.group_id or old.id,
            effective_from=upcoming,
        )
        old.effective_to = upcoming - timedelta(days=1)
        old.active = False
        self._repo.save_rule(old)
        self._repo.delete_future_open_occurrences(old.id, upcoming)
        self._repo.add_rule(version)
        self.generate_occurrences(owner)
        self._ctx.record("finance.rule_changed", owner, rule_id=version.id, version=version.version,
                         approval_id=approval_id)  # fmt: skip
        return version

    def recurring(self, owner: str) -> list[RecurringRule]:
        return list(self._repo.list_rules(owner))

    def generate_occurrences(self, owner: str, *, horizon_days: int = HORIZON_DAYS) -> int:
        """Idempotent: create expected occurrences up to the horizon; mark overdue ones."""
        today = self._ctx.today(owner)
        created = 0
        for rule in self._repo.list_rules(owner):
            first = max(
                rule.effective_from or rule.rule.start, today - timedelta(days=BACKFILL_DAYS)
            )
            last = today + timedelta(days=horizon_days)
            if rule.effective_to:
                last = min(last, rule.effective_to)
            for due in iter_occurrences(rule.rule, first, last):
                occ = Occurrence(_new_id(), owner, rule.id, rule.version, due, rule.amount_minor)
                created += 1 if self._repo.add_occurrence(occ) else 0
        for occ in self._repo.list_occurrences(
            owner, start=today - timedelta(days=400), end=today - timedelta(days=1)
        ):
            if occ.status in ("expected", "partial"):
                occ.status = "overdue" if occ.status == "expected" else occ.status
                self._repo.save_occurrence(occ)
        return created

    def occurrences(self, owner: str, start: date, end: date) -> list[dict[str, Any]]:
        if end < start or (end - start).days > 400:
            raise LifeError("from/to must be a valid range of at most 400 days.")
        self.generate_occurrences(owner)
        rules = {r.id: r for r in self._repo.list_rules(owner, active_only=False)}
        out = []
        for occ in self._repo.list_occurrences(owner, start=start, end=end):
            rule = rules.get(occ.rule_id)
            out.append(
                {
                    "id": occ.id,
                    "rule_id": occ.rule_id,
                    "title": rule.title if rule else "",
                    "kind": rule.kind if rule else "bill",
                    "due_date": occ.due_date.isoformat(),
                    "expected_minor": occ.expected_minor,
                    "paid_minor": occ.paid_minor,
                    "remaining_minor": max(occ.expected_minor - occ.paid_minor, 0),
                    "status": occ.status,
                    "category_id": rule.category_id if rule else None,
                }
            )
        return out

    def settle(
        self,
        owner: str,
        occurrence_id: str,
        *,
        status: str = "paid",
        amount: Any = None,
        created_by: str = "user",
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        """Mark an occurrence paid/received, partial, or skipped; creates the linked transaction."""
        occ = self._repo.get_occurrence(owner, occurrence_id)
        if occ is None:
            raise not_found("Occurrence")
        if occ.status not in OPEN_OCC:
            raise LifeConflict(f"This item is already {occ.status}.")
        rule = self._repo.get_rule(owner, occ.rule_id)
        if rule is None:
            raise not_found("Recurring rule")
        if status == "skipped":
            occ.status = "skipped"
            self._repo.save_occurrence(occ)
            return {"occurrence": self._occ_payload(occ), "transaction": None}
        if status not in ("paid", "partial"):
            raise LifeError("status must be paid, partial or skipped.")
        remaining = occ.expected_minor - occ.paid_minor
        minor = to_minor(amount) if amount not in (None, "") else remaining
        if status == "partial" and minor >= remaining:
            raise LifeError("A partial payment must be less than the remaining amount.")
        tx = self.record(
            owner,
            {
                "kind": "income" if rule.kind == "income" else "expense",
                "amount": minor / 100,
                "account_id": rule.account_id,
                "category_id": rule.category_id,
                "merchant": rule.title,
                "occurred_at": self._ctx.now().isoformat(),
                "status": "received"
                if rule.kind == "income"
                else ("partial" if status == "partial" else "paid"),
            },
            created_by=created_by,
            approval_id=approval_id,
            occurrence_id=occ.id,
        )[0]
        occ.paid_minor += minor
        occ.transaction_id = tx.id
        occ.status = "paid" if occ.paid_minor >= occ.expected_minor else "partial"
        self._repo.save_occurrence(occ)
        return {"occurrence": self._occ_payload(occ), "transaction": dict(tx_payload(tx))}

    @staticmethod
    def _occ_payload(occ: Occurrence) -> dict[str, Any]:
        return {
            "id": occ.id,
            "status": occ.status,
            "paid_minor": occ.paid_minor,
            "remaining_minor": max(occ.expected_minor - occ.paid_minor, 0),
            "due_date": occ.due_date.isoformat(),
        }

    # -- budgets ---------------------------------------------------------------------------

    def create_budget(self, owner: str, data: Mapping[str, Any]) -> Budget:
        _only(
            data,
            {
                "name",
                "type",
                "period",
                "period_start",
                "period_end",
                "income_plan",
                "rollover",
                "lines",
            },
        )
        kind = str(data.get("type") or "monthly")
        if kind not in BUDGET_TYPES:
            raise LifeError(f"type must be one of: {', '.join(BUDGET_TYPES)}.")
        if data.get("period"):
            first, last = month_bounds(str(data["period"]))
        elif data.get("period_start") and data.get("period_end"):
            try:
                first = date.fromisoformat(str(data["period_start"]))
                last = date.fromisoformat(str(data["period_end"]))
            except ValueError as exc:
                raise LifeError("period_start/period_end must be YYYY-MM-DD.") from exc
            if last < first:
                raise LifeError("period_end must not be before period_start.")
        else:
            raise LifeError("Give period (2026-11) or period_start and period_end.")
        if kind == "monthly":
            for existing in self._repo.list_budgets(owner):
                if existing.type == "monthly" and existing.period_start == first:
                    raise LifeConflict("There is already a monthly budget for that month.")
        default_name = data.get("name") or f"{kind.title()} {first:%Y-%m}"
        budget = Budget(
            _new_id(), owner,
            clean_text(default_name, "name", 80, required=True),
            kind, first, last,
            to_minor(data["income_plan"], "income_plan") if data.get("income_plan") else 0,
            bool(data.get("rollover", False)),
        )  # fmt: skip
        if data.get("lines"):
            budget.lines = self._lines(owner, data["lines"])
        self._repo.add_budget(budget)
        self._ctx.record("finance.budget_created", owner, budget_id=budget.id)
        return budget

    def _lines(self, owner: str, raw: Any) -> list[BudgetLine]:
        if not isinstance(raw, Sequence) or isinstance(raw, str):
            raise LifeError("lines must be a list.")
        lines: dict[str, BudgetLine] = {}
        for item in raw:
            if not isinstance(item, Mapping):
                raise LifeError("Each line needs category_id and planned.")
            _only(item, {"category_id", "planned", "alert_at_pct"})
            category_id = str(item.get("category_id") or "")
            if self._repo.get_category(owner, category_id) is None:
                raise not_found("Category")
            pct = item.get("alert_at_pct", ALERT_DEFAULT_PCT)
            if isinstance(pct, bool) or not isinstance(pct, int) or not 1 <= pct <= 100:
                raise LifeError("alert_at_pct must be 1 to 100.")
            lines[category_id] = BudgetLine(
                category_id, to_minor(item.get("planned"), "planned"), pct
            )
        return list(lines.values())

    def set_lines(
        self, owner: str, budget_id: str, raw: Any, *, approval_id: str | None = None
    ) -> Budget:
        budget = self.get_budget(owner, budget_id)
        budget.lines = self._lines(owner, raw)
        self._repo.save_budget(budget)
        self._ctx.record(
            "finance.budget_lines", owner, budget_id=budget_id, approval_id=approval_id
        )
        return budget

    def copy_budget(self, owner: str, budget_id: str, period: str) -> Budget:
        source = self.get_budget(owner, budget_id)
        return self.create_budget(
            owner,
            {
                "name": source.name,
                "type": source.type,
                "period": period,
                "income_plan": source.income_plan_minor / 100 if source.income_plan_minor else None,
                "rollover": source.rollover,
                "lines": [
                    {"category_id": ln.category_id, "planned": ln.planned_minor / 100,
                     "alert_at_pct": ln.alert_at_pct} for ln in source.lines
                ],
            },
        )  # fmt: skip

    def get_budget(self, owner: str, budget_id: str) -> Budget:
        budget = self._repo.get_budget(owner, budget_id)
        if budget is None:
            raise not_found("Budget")
        return budget

    def budget_view(self, owner: str, budget: Budget) -> dict[str, Any]:
        """Budget with per-category actuals, remaining, utilisation and colour status."""
        actual = self._spend_by_category(owner, budget.period_start, budget.period_end)
        names = {c.id: c.name for c in self._repo.list_categories(owner)}
        lines: list[dict[str, Any]] = []
        for ln in budget.lines:
            spent = actual.get(ln.category_id, 0)
            lines.append(
                {
                    "category_id": ln.category_id,
                    "category": names.get(ln.category_id, ""),
                    "planned_minor": ln.planned_minor,
                    "actual_minor": spent,
                    "remaining_minor": ln.planned_minor - spent,
                    "overspend_minor": max(0, spent - ln.planned_minor),
                    "utilisation_pct": utilisation_pct(spent, ln.planned_minor),
                    "status": budget_status(spent, ln.planned_minor, ln.alert_at_pct),
                    "alert_at_pct": ln.alert_at_pct,
                }
            )
        lines.sort(key=lambda x: -x["utilisation_pct"])
        planned = sum(ln.planned_minor for ln in budget.lines)
        return {
            "id": budget.id,
            "name": budget.name,
            "type": budget.type,
            "period_start": budget.period_start.isoformat(),
            "period_end": budget.period_end.isoformat(),
            "income_plan_minor": budget.income_plan_minor,
            "planned_minor": planned,
            "unallocated_minor": budget.income_plan_minor - planned,
            "actual_minor": sum(x["actual_minor"] for x in lines),
            "lines": lines,
        }

    def budgets(self, owner: str) -> list[dict[str, Any]]:
        return [self.budget_view(owner, b) for b in self._repo.list_budgets(owner)]

    def _spend_by_category(self, owner: str, first: date, last: date) -> dict[str, int]:
        start, end = self._range(owner, first, last)
        totals: dict[str, int] = defaultdict(int)
        for tx in self._repo.query_tx(owner, start=start, end=end, kind="expense", limit=100000):
            totals[tx.category_id or UNKNOWN] += tx.amount_minor
        return dict(totals)

    # -- savings goals ---------------------------------------------------------------------

    def create_savings_goal(self, owner: str, data: Mapping[str, Any]) -> SavingsGoal:
        _only(
            data, {"name", "target", "target_date", "monthly_contribution", "account_id", "goal_id"}
        )
        target_date = None
        if data.get("target_date"):
            try:
                target_date = date.fromisoformat(str(data["target_date"]))
            except ValueError as exc:
                raise LifeError("target_date must be YYYY-MM-DD.") from exc
        if (
            data.get("account_id")
            and self._repo.get_account(owner, str(data["account_id"])) is None
        ):
            raise not_found("Account")
        monthly = (
            to_minor(data["monthly_contribution"], "monthly_contribution")
            if data.get("monthly_contribution")
            else 0
        )
        goal = SavingsGoal(
            _new_id(), owner, clean_text(data.get("name"), "name", 120, required=True),
            to_minor(data.get("target"), "target"), data.get("goal_id") or None, target_date,
            monthly,
            data.get("account_id") or None,
        )  # fmt: skip
        self._repo.add_savings_goal(goal)
        return goal

    def contribute(
        self, owner: str, goal_id: str, amount: Any, *, on: date | None = None,
        created_by: str = "user", approval_id: str | None = None,
    ) -> Contribution:  # fmt: skip
        goal = self._repo.get_savings_goal(owner, goal_id)
        if goal is None:
            raise not_found("Savings goal")
        minor = to_minor(amount)
        day = on or self._ctx.today(owner)
        tx_id = None
        if goal.account_id:
            source = next(
                (
                    a
                    for a in self._repo.list_accounts(owner)
                    if a.id != goal.account_id and not a.archived
                ),
                None,
            )
            if source is not None:
                legs = self.record(
                    owner,
                    {"kind": "transfer", "amount": minor / 100, "account_id": source.id,
                     "to_account_id": goal.account_id, "note": f"Savings: {goal.name}",
                     "occurred_at": day.isoformat()},
                    created_by=created_by, approval_id=approval_id,
                )  # fmt: skip
                tx_id = legs[0].id
        contribution = Contribution(_new_id(), goal.id, tx_id, minor, day)
        self._repo.add_contribution(contribution)
        return contribution

    def savings_goals(self, owner: str) -> list[dict[str, Any]]:
        today = self._ctx.today(owner)
        out = []
        for goal in self._repo.list_savings_goals(owner):
            contributions = self._repo.list_contributions(goal.id)
            saved = sum(c.amount_minor for c in contributions)
            done = projected_completion(goal, saved, today)
            out.append(
                {
                    "id": goal.id,
                    "name": goal.name,
                    "target_minor": goal.target_minor,
                    "saved_minor": saved,
                    "progress_pct": round(min(saved / goal.target_minor, 1) * 100, 1),
                    "target_date": goal.target_date.isoformat() if goal.target_date else None,
                    "monthly_contribution_minor": goal.monthly_contribution_minor,
                    "projected_completion": done.isoformat() if done else None,
                    "on_track": (done <= goal.target_date) if (done and goal.target_date) else None,
                    "contributions": [
                        {"amount_minor": c.amount_minor, "on": c.contributed_on.isoformat()}
                        for c in contributions[-12:]
                    ],
                }
            )
        return out

    # -- summary, reports, affordability --------------------------------------------------

    def _month(self, owner: str, period: str | None) -> tuple[str, date, date]:
        if not period:
            today = self._ctx.today(owner)
            period = f"{today:%Y-%m}"
        first, last = month_bounds(period)
        return period, first, last

    def totals(self, owner: str, first: date, last: date) -> dict[str, int]:
        start, end = self._range(owner, first, last)
        names = {c.id: c.name for c in self._repo.list_categories(owner)}
        income = spent = saved = 0
        for tx in self._repo.query_tx(owner, start=start, end=end, limit=100000):
            if tx.kind == "income":
                income += tx.amount_minor
            elif tx.kind == "expense":
                if names.get(tx.category_id or "") in SAVINGS_CATEGORIES:
                    saved += tx.amount_minor  # savings are not spending
                else:
                    spent += tx.amount_minor
        return {"income_minor": income, "spent_minor": spent, "saved_minor": saved}

    def summary(self, owner: str, period: str | None = None) -> dict[str, Any]:
        self.ensure_setup(owner)
        self.generate_occurrences(owner)
        period, first, last = self._month(owner, period)
        today = self._ctx.today(owner)
        totals = self.totals(owner, first, last)
        budget = next(
            (
                b
                for b in self._repo.list_budgets(owner)
                if b.type == "monthly" and b.period_start == first
            ),
            None,
        )
        view = self.budget_view(owner, budget) if budget else None
        planned = view["planned_minor"] if view else 0
        spent_all = totals["spent_minor"] + totals["saved_minor"]
        upcoming = [
            o
            for o in self.occurrences(owner, today, today + timedelta(days=14))
            if o["status"] in OPEN_OCC
        ]
        month_occ = self.occurrences(owner, max(first, today - timedelta(days=60)), last)
        in_month = [
            o
            for o in month_occ
            if o["status"] in OPEN_OCC and today.isoformat() <= o["due_date"] <= last.isoformat()
        ]
        open_bills = sum(o["remaining_minor"] for o in in_month if o["kind"] == "bill")
        open_income = sum(o["remaining_minor"] for o in in_month if o["kind"] == "income")
        days_left = (last - today).days if first <= today <= last else 0
        avg = self._avg_daily_variable(owner, today)
        balance = sum(self.balances(owner).values())
        return {
            "period": period,
            **totals,
            "budget_planned_minor": planned,
            "left_in_budget_minor": (planned - spent_all) if view else None,
            "savings_rate_pct": savings_rate_pct(totals["income_minor"], totals["spent_minor"]),
            "balance_minor": balance,
            "expected_end_balance_minor": expected_end_balance(
                balance, open_income, open_bills, avg, days_left
            ),
            "avg_daily_variable_minor": avg,
            "budget": view,
            "upcoming": upcoming,
            "currency": DEFAULT_CURRENCY,
        }

    def _avg_daily_variable(self, owner: str, today: date) -> int:
        start, end = self._range(owner, today - timedelta(days=29), today)
        fixed_ids = {c.id for c in self._repo.list_categories(owner) if c.is_fixed}
        total = sum(
            tx.amount_minor
            for tx in self._repo.query_tx(owner, start=start, end=end, kind="expense", limit=100000)
            if tx.category_id not in fixed_ids
        )
        return total // 30

    def today_row(self, owner: str) -> dict[str, Any]:
        """Money row for Today: spent today, left this month, next bill."""
        self.ensure_setup(owner)
        self.generate_occurrences(owner)
        today = self._ctx.today(owner)
        start, end = self._range(owner, today, today)
        spent = sum(
            t.amount_minor
            for t in self._repo.query_tx(owner, start=start, end=end, kind="expense", limit=10000)
        )
        first, last = month_bounds(f"{today:%Y-%m}")
        budget = next(
            (
                b
                for b in self._repo.list_budgets(owner)
                if b.type == "monthly" and b.period_start == first
            ),
            None,
        )
        left = None
        if budget:
            view = self.budget_view(owner, budget)
            left = view["planned_minor"] - view["actual_minor"]
        bills = [o for o in self.occurrences(owner, today, today + timedelta(days=60))
                 if o["kind"] == "bill" and o["status"] in OPEN_OCC]  # fmt: skip
        nxt = bills[0] if bills else None
        return {
            "spent_today_minor": spent,
            "left_this_month_minor": left,
            "next_bill": nxt,
            "currency": DEFAULT_CURRENCY,
        }

    def report(
        self, owner: str, kind: str, period: str | None = None, months: int = 6
    ) -> dict[str, Any]:
        self.ensure_setup(owner)
        period, first, last = self._month(owner, period)
        if kind == "category":
            names = {c.id: c.name for c in self._repo.list_categories(owner)}
            rows: list[dict[str, Any]] = [
                {"category_id": k, "category": names.get(k, "Uncategorised"), "amount_minor": v}
                for k, v in self._spend_by_category(owner, first, last).items()
            ]
            rows.sort(key=lambda r: -r["amount_minor"])
            return {"period": period, "rows": rows}
        if kind == "monthly":
            if not 1 <= months <= 24:
                raise LifeError("months must be 1 to 24.")
            rows = []
            year, month = first.year, first.month
            for _ in range(months):
                m_first, m_last = month_bounds(f"{year:04d}-{month:02d}")
                rows.append(
                    {"period": f"{year:04d}-{month:02d}", **self.totals(owner, m_first, m_last)}
                )
                month -= 1
                if month == 0:
                    year, month = year - 1, 12
            rows.reverse()
            return {"rows": rows}
        raise LifeError("report must be monthly or category.")

    def query(
        self, owner: str, *, period: str | None = None, category: str = "", merchant: str = ""
    ) -> dict[str, Any]:
        """Agent read: spend by period/category/merchant, answered from real rows only."""
        self.ensure_setup(owner)
        period, first, last = self._month(owner, period)
        category_id = None
        if category:
            match = next(
                (
                    c
                    for c in self._repo.list_categories(owner)
                    if c.name.lower() == category.lower()
                ),
                None,
            )
            if match is None:
                raise LifeError(f"No category named '{category}'.")
            category_id = match.id
        txs = self.transactions(
            owner, period=period, category_id=category_id, text=merchant, limit=500
        )
        spent = sum(t.amount_minor for t in txs if t.kind == "expense")
        income = sum(t.amount_minor for t in txs if t.kind == "income")
        return {
            "period": period,
            "count": len(txs),
            "spent_minor": spent,
            "income_minor": income,
            "message": None if txs else f"No transactions recorded for {first} to {last}.",
        }

    def affordability(self, owner: str, amount: Any, category: str = "") -> dict[str, Any]:
        minor = to_minor(amount)
        summary = self.summary(owner)
        left = summary["left_in_budget_minor"]
        end_balance = summary["expected_end_balance_minor"] - minor
        category_left = None
        if category and summary["budget"]:
            line = next(
                (
                    x
                    for x in summary["budget"]["lines"]
                    if x["category"].lower() == category.lower()
                ),
                None,
            )
            category_left = line["remaining_minor"] - minor if line else None
        return {
            "amount_minor": minor,
            "left_in_budget_after_minor": None if left is None else left - minor,
            "category_left_after_minor": category_left,
            "expected_end_balance_after_minor": end_balance,
            "affordable": end_balance >= 0 and (left is None or left - minor >= 0),
            "note": format_money(minor) + " against this month's budget and expected balance.",
        }

    def budget_alerts(self, owner: str) -> list[dict[str, Any]]:
        """Categories at/over their alert threshold this month (for proactive notices)."""
        summary = self.summary(owner)
        view = summary["budget"]
        if not view:
            return []
        today = self._ctx.today(owner)
        first, last = month_bounds(summary["period"])
        days_left = (last - today).days
        return [
            {
                "category": ln["category"],
                "status": ln["status"],
                "utilisation_pct": ln["utilisation_pct"],
                "remaining_minor": ln["remaining_minor"],
                "days_left": days_left,
            }
            for ln in view["lines"]
            if ln["status"] in ("amber", "red")
        ]

    def nudge_text(self, owner: str) -> str | None:
        """Budget thresholds and bills due soon, from real rows; None when all is calm."""
        lines: list[str] = []
        for alert in self.budget_alerts(owner)[:2]:
            word = "over" if alert["status"] == "red" else "at"
            lines.append(
                f"{alert['category']} is {word} {round(alert['utilisation_pct'])}% of its budget "
                f"({format_money(max(alert['remaining_minor'], 0))} left, "
                f"{alert['days_left']} days to go)."
            )
        for occ in self.due_soon(owner)[:2]:
            verb = "expected" if occ["kind"] == "income" else "due"
            lines.append(
                f"{occ['title']} {verb} {occ['due_date']}: {format_money(occ['remaining_minor'])}."
            )
        return " ".join(lines) or None

    def due_soon(self, owner: str) -> list[dict[str, Any]]:
        """Bills inside their reminder window or overdue, and income due today."""
        today = self._ctx.today(owner)
        rules = {r.id: r for r in self._repo.list_rules(owner)}
        out = []
        for occ in self.occurrences(owner, today - timedelta(days=30), today + timedelta(days=30)):
            rule = rules.get(occ.get("rule_id", ""))
            if rule is None or occ["status"] not in OPEN_OCC:
                continue
            due = date.fromisoformat(occ["due_date"])
            if (rule.kind == "bill" and due - today <= timedelta(days=rule.remind_days_before)) or (
                rule.kind == "income" and due == today
            ):
                out.append(occ)
        return out
