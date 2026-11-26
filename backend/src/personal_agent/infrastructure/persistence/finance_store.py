"""SQLAlchemy repository for the finance ledger (section 6.3)."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from personal_agent.domain.finance import (
    Account,
    Budget,
    BudgetLine,
    Category,
    Contribution,
    Occurrence,
    RecurringRule,
    SavingsGoal,
    Transaction,
)
from personal_agent.domain.life import LifeConflict
from personal_agent.domain.recurrence import parse_rule
from personal_agent.infrastructure.persistence.database import session_scope
from personal_agent.infrastructure.persistence.models import (
    FinAccountRow,
    FinBudgetLineRow,
    FinBudgetRow,
    FinCategoryRow,
    FinContributionRow,
    FinOccurrenceRow,
    FinRecurringRuleRow,
    FinSavingsGoalRow,
    FinTransactionRow,
)


def _aware(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def _copy(row: Any, obj: Any, fields: Sequence[str]) -> None:
    for name in fields:
        setattr(row, name, getattr(obj, name))


_ACCOUNT = ("owner_user_id", "name", "type", "currency", "opening_balance_minor", "archived")
_CATEGORY = ("owner_user_id", "parent_id", "name", "kind", "icon", "is_fixed")
_TX = (
    "owner_user_id",
    "account_id",
    "category_id",
    "kind",
    "amount_minor",
    "currency",
    "occurred_at",
    "status",
    "merchant",
    "note",
    "budget_id",
    "project_id",
    "occurrence_id",
    "transfer_group",
    "receipt_file_id",
    "created_by",
    "approval_id",
    "deleted_at",
)
_OCC = (
    "owner_user_id",
    "rule_id",
    "rule_version",
    "due_date",
    "expected_minor",
    "status",
    "paid_minor",
    "transaction_id",
)
_GOAL = (
    "owner_user_id",
    "name",
    "goal_id",
    "target_minor",
    "target_date",
    "monthly_contribution_minor",
    "account_id",
    "currency",
)


class FinanceRepositoryImpl:
    def __init__(self, factory: sessionmaker[Session]) -> None:
        self._factory = factory

    # -- accounts / categories -------------------------------------------------------------

    @staticmethod
    def _account(r: FinAccountRow) -> Account:
        return Account(
            r.id, r.owner_user_id, r.name, r.type, r.currency, r.opening_balance_minor, r.archived
        )

    def list_accounts(self, owner: str) -> Sequence[Account]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinAccountRow)
                .where(FinAccountRow.owner_user_id == owner)
                .order_by(FinAccountRow.name)
            )
            return [self._account(r) for r in rows]

    def add_account(self, account: Account) -> None:
        with session_scope(self._factory) as s:
            row = FinAccountRow(id=account.id)
            _copy(row, account, _ACCOUNT)
            s.add(row)
            try:
                s.flush()
            except IntegrityError as exc:
                raise LifeConflict("An account with that name already exists.") from exc

    def save_account(self, account: Account) -> None:
        with session_scope(self._factory) as s:
            row = s.get(FinAccountRow, account.id)
            if row is None or row.owner_user_id != account.owner_user_id:
                return
            _copy(row, account, _ACCOUNT)
            try:
                s.flush()
            except IntegrityError as exc:
                raise LifeConflict("An account with that name already exists.") from exc

    def get_account(self, owner: str, account_id: str) -> Account | None:
        with session_scope(self._factory) as s:
            row = s.get(FinAccountRow, account_id)
            return self._account(row) if row and row.owner_user_id == owner else None

    @staticmethod
    def _category(r: FinCategoryRow) -> Category:
        return Category(r.id, r.owner_user_id, r.name, r.kind, r.parent_id, r.icon, r.is_fixed)

    def list_categories(self, owner: str) -> Sequence[Category]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinCategoryRow)
                .where(FinCategoryRow.owner_user_id == owner)
                .order_by(FinCategoryRow.kind, FinCategoryRow.name)
            )
            return [self._category(r) for r in rows]

    def add_category(self, category: Category) -> None:
        with session_scope(self._factory) as s:
            row = FinCategoryRow(id=category.id)
            _copy(row, category, _CATEGORY)
            s.add(row)
            try:
                s.flush()
            except IntegrityError as exc:
                raise LifeConflict("A category with that name already exists.") from exc

    def get_category(self, owner: str, category_id: str) -> Category | None:
        with session_scope(self._factory) as s:
            row = s.get(FinCategoryRow, category_id)
            return self._category(row) if row and row.owner_user_id == owner else None

    # -- transactions ----------------------------------------------------------------------

    @staticmethod
    def _tx(r: FinTransactionRow) -> Transaction:
        tx = Transaction(
            id=r.id,
            owner_user_id=r.owner_user_id,
            kind=r.kind,
            amount_minor=r.amount_minor,
            currency=r.currency,
            occurred_at=_aware(r.occurred_at),  # type: ignore[arg-type]
        )
        for name in _TX:
            if name not in ("occurred_at", "deleted_at"):
                setattr(tx, name, getattr(r, name))
        tx.deleted_at = _aware(r.deleted_at)
        tx.created_at = _aware(r.created_at)
        return tx

    def add_tx(self, tx: Transaction) -> None:
        with session_scope(self._factory) as s:
            row = FinTransactionRow(id=tx.id, created_at=tx.created_at or datetime.now(UTC))
            _copy(row, tx, _TX)
            s.add(row)

    def get_tx(self, owner: str, tx_id: str) -> Transaction | None:
        with session_scope(self._factory) as s:
            row = s.get(FinTransactionRow, tx_id)
            return self._tx(row) if row and row.owner_user_id == owner else None

    def save_tx(self, tx: Transaction) -> None:
        with session_scope(self._factory) as s:
            row = s.get(FinTransactionRow, tx.id)
            if row is not None:
                _copy(row, tx, _TX)

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
    ) -> Sequence[Transaction]:
        with session_scope(self._factory) as s:
            stmt = select(FinTransactionRow).where(
                FinTransactionRow.owner_user_id == owner, FinTransactionRow.deleted_at.is_(None)
            )
            if start is not None:
                stmt = stmt.where(FinTransactionRow.occurred_at >= start)
            if end is not None:
                stmt = stmt.where(FinTransactionRow.occurred_at < end)
            if category_id:
                stmt = stmt.where(FinTransactionRow.category_id == category_id)
            if account_id:
                stmt = stmt.where(FinTransactionRow.account_id == account_id)
            if kind:
                stmt = stmt.where(FinTransactionRow.kind == kind)
            if text:
                needle = text.lower()
                stmt = stmt.where(
                    or_(
                        func.lower(FinTransactionRow.merchant).contains(needle, autoescape=True),
                        func.lower(FinTransactionRow.note).contains(needle, autoescape=True),
                    )
                )
            stmt = (
                stmt.order_by(FinTransactionRow.occurred_at.desc(), FinTransactionRow.id)
                .limit(limit)
                .offset(offset)
            )
            return [self._tx(r) for r in s.scalars(stmt)]

    # -- recurring -------------------------------------------------------------------------

    @staticmethod
    def _rule(r: FinRecurringRuleRow) -> RecurringRule:
        return RecurringRule(
            id=r.id,
            owner_user_id=r.owner_user_id,
            kind=r.kind,
            title=r.title,
            amount_minor=r.amount_minor,
            rule=parse_rule(r.rule or {}),
            category_id=r.category_id,
            account_id=r.account_id,
            remind_days_before=r.remind_days_before,
            version=r.version,
            active=bool(r.active),
            group_id=r.group_id,
            effective_from=r.effective_from,
            effective_to=r.effective_to,
        )

    @staticmethod
    def _fill_rule(row: FinRecurringRuleRow, rule: RecurringRule) -> None:
        for name in (
            "owner_user_id",
            "kind",
            "title",
            "amount_minor",
            "category_id",
            "account_id",
            "remind_days_before",
            "version",
            "active",
            "group_id",
            "effective_from",
            "effective_to",
        ):
            setattr(row, name, getattr(rule, name))
        row.rule = rule.rule.to_dict()

    def add_rule(self, rule: RecurringRule) -> None:
        with session_scope(self._factory) as s:
            row = FinRecurringRuleRow(id=rule.id)
            self._fill_rule(row, rule)
            s.add(row)

    def get_rule(self, owner: str, rule_id: str) -> RecurringRule | None:
        with session_scope(self._factory) as s:
            row = s.get(FinRecurringRuleRow, rule_id)
            return self._rule(row) if row and row.owner_user_id == owner else None

    def save_rule(self, rule: RecurringRule) -> None:
        with session_scope(self._factory) as s:
            row = s.get(FinRecurringRuleRow, rule.id)
            if row is not None:
                self._fill_rule(row, rule)

    def list_rules(self, owner: str, *, active_only: bool = True) -> Sequence[RecurringRule]:
        with session_scope(self._factory) as s:
            stmt = select(FinRecurringRuleRow).where(FinRecurringRuleRow.owner_user_id == owner)
            if active_only:
                stmt = stmt.where(FinRecurringRuleRow.active.is_(True))
            return [self._rule(r) for r in s.scalars(stmt.order_by(FinRecurringRuleRow.title))]

    @staticmethod
    def _occ(r: FinOccurrenceRow) -> Occurrence:
        return Occurrence(
            r.id,
            r.owner_user_id,
            r.rule_id,
            r.rule_version,
            r.due_date,
            r.expected_minor,
            r.status,
            r.paid_minor,
            r.transaction_id,
        )

    def add_occurrence(self, occ: Occurrence) -> bool:
        """Insert; False when (rule_id, due_date) already exists (idempotent generation)."""
        with session_scope(self._factory) as s:
            exists = s.scalars(
                select(FinOccurrenceRow.id).where(
                    FinOccurrenceRow.rule_id == occ.rule_id,
                    FinOccurrenceRow.due_date == occ.due_date,
                )
            ).first()
            if exists:
                return False
            row = FinOccurrenceRow(id=occ.id)
            _copy(row, occ, _OCC)
            s.add(row)
            return True

    def get_occurrence(self, owner: str, occ_id: str) -> Occurrence | None:
        with session_scope(self._factory) as s:
            row = s.get(FinOccurrenceRow, occ_id)
            return self._occ(row) if row and row.owner_user_id == owner else None

    def save_occurrence(self, occ: Occurrence) -> None:
        with session_scope(self._factory) as s:
            row = s.get(FinOccurrenceRow, occ.id)
            if row is not None:
                _copy(row, occ, _OCC)

    def list_occurrences(self, owner: str, *, start: date, end: date) -> Sequence[Occurrence]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinOccurrenceRow)
                .where(
                    FinOccurrenceRow.owner_user_id == owner,
                    FinOccurrenceRow.due_date >= start,
                    FinOccurrenceRow.due_date <= end,
                )
                .order_by(FinOccurrenceRow.due_date, FinOccurrenceRow.id)
            )
            return [self._occ(r) for r in rows]

    def occurrence_dates(self, rule_id: str) -> set[date]:
        with session_scope(self._factory) as s:
            return set(
                s.scalars(
                    select(FinOccurrenceRow.due_date).where(FinOccurrenceRow.rule_id == rule_id)
                )
            )

    def delete_future_open_occurrences(self, rule_id: str, from_day: date) -> int:
        with session_scope(self._factory) as s:
            result = s.execute(
                delete(FinOccurrenceRow).where(
                    FinOccurrenceRow.rule_id == rule_id,
                    FinOccurrenceRow.due_date >= from_day,
                    FinOccurrenceRow.status == "expected",
                )
            )
            return int(result.rowcount or 0)  # type: ignore[attr-defined]

    # -- budgets ---------------------------------------------------------------------------

    @staticmethod
    def _budget(s: Session, r: FinBudgetRow) -> Budget:
        lines = s.scalars(
            select(FinBudgetLineRow)
            .where(FinBudgetLineRow.budget_id == r.id)
            .order_by(FinBudgetLineRow.id)
        )
        return Budget(
            r.id,
            r.owner_user_id,
            r.name,
            r.type,
            r.period_start,
            r.period_end,
            r.income_plan_minor,
            r.rollover,
            [BudgetLine(x.category_id, x.planned_minor, x.alert_at_pct) for x in lines],
        )

    @staticmethod
    def _write_budget(s: Session, row: FinBudgetRow, budget: Budget) -> None:
        for name in (
            "owner_user_id",
            "name",
            "type",
            "period_start",
            "period_end",
            "income_plan_minor",
            "rollover",
        ):
            setattr(row, name, getattr(budget, name))
        s.flush()
        s.execute(delete(FinBudgetLineRow).where(FinBudgetLineRow.budget_id == row.id))
        for line in budget.lines:
            s.add(
                FinBudgetLineRow(
                    budget_id=row.id,
                    category_id=line.category_id,
                    planned_minor=line.planned_minor,
                    alert_at_pct=line.alert_at_pct,
                )
            )

    def add_budget(self, budget: Budget) -> None:
        with session_scope(self._factory) as s:
            row = FinBudgetRow(id=budget.id)
            s.add(row)
            self._write_budget(s, row, budget)

    def get_budget(self, owner: str, budget_id: str) -> Budget | None:
        with session_scope(self._factory) as s:
            row = s.get(FinBudgetRow, budget_id)
            return self._budget(s, row) if row and row.owner_user_id == owner else None

    def save_budget(self, budget: Budget) -> None:
        with session_scope(self._factory) as s:
            row = s.get(FinBudgetRow, budget.id)
            if row is not None:
                self._write_budget(s, row, budget)

    def delete_budget(self, owner: str, budget_id: str) -> bool:
        """Remove a budget and its lines; transactions that pointed at it keep their data."""
        with session_scope(self._factory) as s:
            row = s.get(FinBudgetRow, budget_id)
            if row is None or row.owner_user_id != owner:
                return False
            s.execute(delete(FinBudgetLineRow).where(FinBudgetLineRow.budget_id == budget_id))
            s.execute(
                update(FinTransactionRow)
                .where(
                    FinTransactionRow.owner_user_id == owner,
                    FinTransactionRow.budget_id == budget_id,
                )
                .values(budget_id=None)
            )
            s.delete(row)
            return True

    def list_budgets(self, owner: str) -> Sequence[Budget]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinBudgetRow)
                .where(FinBudgetRow.owner_user_id == owner)
                .order_by(FinBudgetRow.period_start.desc(), FinBudgetRow.id)
            )
            return [self._budget(s, r) for r in rows]

    # -- savings ---------------------------------------------------------------------------

    @staticmethod
    def _goal(r: FinSavingsGoalRow) -> SavingsGoal:
        return SavingsGoal(
            r.id,
            r.owner_user_id,
            r.name,
            r.target_minor,
            r.goal_id,
            r.target_date,
            r.monthly_contribution_minor,
            r.account_id,
            r.currency,
        )

    def add_savings_goal(self, goal: SavingsGoal) -> None:
        with session_scope(self._factory) as s:
            row = FinSavingsGoalRow(id=goal.id)
            _copy(row, goal, _GOAL)
            s.add(row)

    def get_savings_goal(self, owner: str, goal_id: str) -> SavingsGoal | None:
        with session_scope(self._factory) as s:
            row = s.get(FinSavingsGoalRow, goal_id)
            return self._goal(row) if row and row.owner_user_id == owner else None

    def list_savings_goals(self, owner: str) -> Sequence[SavingsGoal]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinSavingsGoalRow)
                .where(FinSavingsGoalRow.owner_user_id == owner)
                .order_by(FinSavingsGoalRow.name)
            )
            return [self._goal(r) for r in rows]

    def add_contribution(self, contribution: Contribution) -> None:
        with session_scope(self._factory) as s:
            s.add(
                FinContributionRow(
                    id=contribution.id,
                    savings_goal_id=contribution.savings_goal_id,
                    transaction_id=contribution.transaction_id,
                    amount_minor=contribution.amount_minor,
                    contributed_on=contribution.contributed_on,
                )
            )

    def list_contributions(self, goal_id: str) -> Sequence[Contribution]:
        with session_scope(self._factory) as s:
            rows = s.scalars(
                select(FinContributionRow)
                .where(FinContributionRow.savings_goal_id == goal_id)
                .order_by(FinContributionRow.contributed_on, FinContributionRow.id)
            )
            return [
                Contribution(
                    r.id, r.savings_goal_id, r.transaction_id, r.amount_minor, r.contributed_on
                )
                for r in rows
            ]
