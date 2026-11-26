"""Finance API (section 6.4). Typed bodies reject unknown fields with 422."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Query, Response
from pydantic import BaseModel, ConfigDict, Field

from personal_agent.app.container import AppContainer
from personal_agent.application.services.day_service import parse_day
from personal_agent.domain.finance import tx_payload
from personal_agent.presentation.web.routers._common import DASHBOARD_OWNER

Amount = str | int | float


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class TxIn(_Strict):
    kind: str = "expense"
    amount: Amount
    occurred_at: str | None = None
    account_id: str | None = None
    to_account_id: str | None = None
    category_id: str | None = None
    merchant: str = ""
    note: str = ""
    budget_id: str | None = None
    project_id: str | None = None
    status: str | None = None
    receipt_file_id: str | None = None


class TxPatch(_Strict):
    amount: Amount | None = None
    occurred_at: str | None = None
    account_id: str | None = None
    category_id: str | None = None
    merchant: str | None = None
    note: str | None = None
    budget_id: str | None = None
    project_id: str | None = None
    status: str | None = None
    receipt_file_id: str | None = None


class QuickIn(_Strict):
    amount: Amount
    category_id: str | None = None


class ParseIn(_Strict):
    text: str


class RuleBody(_Strict):
    freq: str
    interval: int = 1
    weekdays: list[int] = Field(default_factory=list)
    day_of_month: int | None = None
    start: str | None = None
    end: str | None = None


class RecurringIn(_Strict):
    kind: str = "bill"
    title: str
    amount: Amount
    rule: RuleBody
    category_id: str | None = None
    account_id: str | None = None
    remind_days_before: int = 3


class RecurringPatch(_Strict):
    title: str | None = None
    amount: Amount | None = None
    rule: RuleBody | None = None
    category_id: str | None = None
    account_id: str | None = None
    remind_days_before: int | None = None


class SettleIn(_Strict):
    status: str = "paid"
    amount: Amount | None = None


class LineIn(_Strict):
    category_id: str
    planned: Amount
    alert_at_pct: int = 80


class BudgetIn(_Strict):
    name: str | None = None
    type: str = "monthly"
    period: str | None = None
    period_start: str | None = None
    period_end: str | None = None
    income_plan: Amount | None = None
    rollover: bool = False
    lines: list[LineIn] | None = None


class CopyIn(_Strict):
    period: str


class AccountIn(_Strict):
    name: str
    type: str = "cash"
    currency: str = "ETB"
    opening_balance: Amount | None = None


class CategoryIn(_Strict):
    name: str
    kind: str = "expense"
    parent_id: str | None = None
    icon: str = ""
    is_fixed: bool = False


class SavingsIn(_Strict):
    name: str
    target: Amount
    target_date: str | None = None
    monthly_contribution: Amount | None = None
    account_id: str | None = None
    goal_id: str | None = None


class ContributionIn(_Strict):
    amount: Amount
    on: str | None = None


def _dump(model: BaseModel, **kw: Any) -> dict[str, Any]:
    return model.model_dump(**kw)


def build_finance_router(container: AppContainer) -> APIRouter:
    router = APIRouter(prefix="/api/finance", tags=["finance"])
    owner = DASHBOARD_OWNER
    fin = container.finance

    def rule_out(rule: Any) -> dict[str, Any]:
        return {
            "id": rule.id,
            "group_id": rule.group_id,
            "version": rule.version,
            "kind": rule.kind,
            "title": rule.title,
            "amount_minor": rule.amount_minor,
            "rule": rule.rule.to_dict(),
            "category_id": rule.category_id,
            "account_id": rule.account_id,
            "remind_days_before": rule.remind_days_before,
            "effective_from": rule.effective_from.isoformat() if rule.effective_from else None,
        }

    # -- setup ---------------------------------------------------------------------
    @router.get("/accounts")
    def accounts() -> list[dict[str, Any]]:
        return fin.accounts(owner)

    @router.post("/accounts", status_code=201)
    def create_account(body: AccountIn) -> dict[str, Any]:
        account = fin.create_account(owner, _dump(body, exclude_none=True))
        return {"id": account.id, "name": account.name, "type": account.type}

    @router.get("/categories")
    def categories() -> list[dict[str, Any]]:
        return fin.categories(owner)

    @router.post("/categories", status_code=201)
    def create_category(body: CategoryIn) -> dict[str, Any]:
        category = fin.create_category(owner, _dump(body, exclude_none=True))
        return {"id": category.id, "name": category.name, "kind": category.kind}

    # -- transactions --------------------------------------------------------------
    @router.get("/transactions")
    def transactions(
        period: str | None = None,
        category_id: str | None = None,
        account_id: str | None = None,
        kind: str | None = None,
        q: str = "",
        limit: Annotated[int, Query(ge=1, le=500)] = 100,
        offset: Annotated[int, Query(ge=0)] = 0,
    ) -> list[dict[str, Any]]:
        rows = fin.transactions(
            owner, period=period, category_id=category_id, account_id=account_id, kind=kind,
            text=q, limit=limit, offset=offset,
        )  # fmt: skip
        return [dict(tx_payload(t)) for t in rows]

    @router.post("/transactions", status_code=201)
    def create_tx(body: TxIn) -> list[dict[str, Any]]:
        return [dict(tx_payload(t)) for t in fin.record(owner, _dump(body, exclude_none=True))]

    @router.post("/transactions/quick", status_code=201)
    def quick(body: QuickIn) -> dict[str, Any]:
        return dict(tx_payload(fin.quick(owner, body.amount, body.category_id)))

    @router.post("/parse")
    def parse(body: ParseIn) -> dict[str, Any]:
        return fin.parse(owner, body.text)

    @router.patch("/transactions/{tx_id}")
    def patch_tx(tx_id: str, body: TxPatch) -> dict[str, Any]:
        return dict(tx_payload(fin.update(owner, tx_id, _dump(body, exclude_unset=True))))

    @router.delete("/transactions/{tx_id}", status_code=204)
    def delete_tx(tx_id: str) -> Response:
        fin.delete(owner, tx_id)
        return Response(status_code=204)

    # -- recurring -----------------------------------------------------------------
    @router.get("/recurring")
    def recurring() -> list[dict[str, Any]]:
        return [rule_out(r) for r in fin.recurring(owner)]

    @router.post("/recurring", status_code=201)
    def create_recurring(body: RecurringIn) -> dict[str, Any]:
        return rule_out(fin.create_recurring(owner, _dump(body, exclude_none=True)))

    @router.patch("/recurring/{rule_id}")
    def change_recurring(rule_id: str, body: RecurringPatch) -> dict[str, Any]:
        return rule_out(fin.change_recurring(owner, rule_id, _dump(body, exclude_unset=True)))

    @router.get("/occurrences")
    def occurrences(
        from_date: Annotated[str | None, Query(alias="from")] = None,
        to_date: Annotated[str | None, Query(alias="to")] = None,
    ) -> list[dict[str, Any]]:
        from datetime import timedelta

        today = container.life_ctx.today(owner)
        start = parse_day(from_date, "from") if from_date else today
        end = parse_day(to_date, "to") if to_date else today + timedelta(days=30)
        return fin.occurrences(owner, start, end)

    @router.post("/occurrences/{occurrence_id}/settle")
    def settle(occurrence_id: str, body: SettleIn) -> dict[str, Any]:
        return fin.settle(owner, occurrence_id, status=body.status, amount=body.amount)

    # -- budgets -------------------------------------------------------------------
    @router.get("/budgets")
    def budgets() -> list[dict[str, Any]]:
        return fin.budgets(owner)

    @router.post("/budgets", status_code=201)
    def create_budget(body: BudgetIn) -> dict[str, Any]:
        budget = fin.create_budget(owner, _dump(body, exclude_none=True))
        return fin.budget_view(owner, budget)

    @router.put("/budgets/{budget_id}/lines")
    def put_lines(budget_id: str, lines: list[LineIn]) -> dict[str, Any]:
        budget = fin.set_lines(owner, budget_id, [_dump(x) for x in lines])
        return fin.budget_view(owner, budget)

    @router.post("/budgets/{budget_id}/copy", status_code=201)
    def copy_budget(budget_id: str, body: CopyIn) -> dict[str, Any]:
        return fin.budget_view(owner, fin.copy_budget(owner, budget_id, body.period))

    # -- savings -------------------------------------------------------------------
    @router.get("/savings-goals")
    def savings_goals() -> list[dict[str, Any]]:
        return fin.savings_goals(owner)

    @router.post("/savings-goals", status_code=201)
    def create_savings(body: SavingsIn) -> dict[str, Any]:
        goal = fin.create_savings_goal(owner, _dump(body, exclude_none=True))
        return {"id": goal.id, "name": goal.name}

    @router.post("/savings-goals/{goal_id}/contributions", status_code=201)
    def contribute(goal_id: str, body: ContributionIn) -> dict[str, Any]:
        item = fin.contribute(
            owner, goal_id, body.amount, on=parse_day(body.on) if body.on else None
        )
        return {
            "id": item.id,
            "amount_minor": item.amount_minor,
            "on": item.contributed_on.isoformat(),
        }

    # -- summary and reports -------------------------------------------------------
    @router.get("/summary")
    def summary(period: str | None = None) -> dict[str, Any]:
        return fin.summary(owner, period)

    @router.get("/alerts")
    def alerts() -> dict[str, Any]:
        return {"budget": fin.budget_alerts(owner), "due": fin.due_soon(owner)}

    @router.get("/reports/{kind}")
    def reports(kind: str, period: str | None = None, months: int = 6) -> dict[str, Any]:
        return fin.report(owner, kind, period, months)

    return router
