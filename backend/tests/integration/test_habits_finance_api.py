"""Habits and finance end to end through the API (roadmap P1-2, P1-3)."""

from __future__ import annotations

from datetime import timedelta

import pytest

from tests.integration.test_tasks_api import _client


@pytest.fixture
def client(tmp_path):
    return _client(tmp_path)


def _iso_today(client) -> str:
    from datetime import UTC, datetime

    return datetime.now(UTC).date().isoformat()


# -- habits ------------------------------------------------------------------------------


def test_habit_checkin_streak_and_today_row(client):
    created = client.post("/api/habits", json={"name": "Prayer", "rule": {"freq": "daily"}})
    assert created.status_code == 201, created.text
    habit = created.json()

    today = client.get("/api/habits/today").json()
    assert today["due"] == 1 and today["done"] == 0
    assert today["items"][0]["status"] == "open"

    r = client.post(f"/api/habits/{habit['id']}/checkins", json={"status": "done"})
    assert r.status_code == 201, r.text
    again = client.post(f"/api/habits/{habit['id']}/checkins", json={"status": "done", "value": 30})
    assert again.status_code == 201  # idempotent per day

    listed = client.get("/api/habits").json()
    assert listed[0]["streak"]["current"] == 1
    assert client.get("/api/habits/today").json()["done"] == 1
    # The Today payload carries the habit row.
    assert client.get("/api/today").json()["habits"]["done"] == 1

    assert (
        client.delete(f"/api/habits/{habit['id']}/checkins/{_iso_today(client)}").status_code == 204
    )
    assert client.get("/api/habits/today").json()["done"] == 0


def test_habit_validation_and_unknown_fields_rejected(client):
    assert (
        client.post("/api/habits", json={"name": "", "rule": {"freq": "daily"}}).status_code == 400
    )
    assert client.post("/api/habits", json={"name": "x", "recurrence": "daily"}).status_code == 422
    habit = client.post("/api/habits", json={"name": "Run", "rule": {"freq": "daily"}}).json()
    future = (__import__("datetime").date.today() + timedelta(days=3)).isoformat()
    assert (
        client.post(f"/api/habits/{habit['id']}/checkins", json={"day": future}).status_code == 400
    )
    skipped = client.post(f"/api/habits/{habit['id']}/checkins", json={"status": "skipped"})
    assert skipped.status_code == 400  # a skip needs a reason
    ok = client.post(
        f"/api/habits/{habit['id']}/checkins", json={"status": "skipped", "note": "sick"}
    )
    assert ok.status_code == 201
    assert client.get("/api/habits/grid").json()["rows"][0]["cells"][-1]["state"] == "skipped"
    assert client.delete(f"/api/habits/{habit['id']}").status_code == 204
    assert client.get("/api/habits").json() == []


# -- finance -----------------------------------------------------------------------------


def _category(client, name, kind="expense"):
    return next(
        c["id"]
        for c in client.get("/api/finance/categories").json()
        if c["name"] == name and c["kind"] == kind
    )


def test_quick_expense_defaults_and_validation(client):
    food = _category(client, "Household & Food")
    r = client.post("/api/finance/transactions/quick", json={"amount": 250, "category_id": food})
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["amount_minor"] == 25000 and body["currency"] == "ETB" and body["kind"] == "expense"
    for bad in (0, -5, "abc", 1.234):
        assert (
            client.post("/api/finance/transactions/quick", json={"amount": bad}).status_code == 400
        )
    assert (
        client.post("/api/finance/transactions", json={"amount": 5, "bogus": 1}).status_code == 422
    )
    # An income category cannot be used for an expense.
    salary = _category(client, "Salary", "income")
    assert (
        client.post(
            "/api/finance/transactions/quick", json={"amount": 5, "category_id": salary}
        ).status_code
        == 400
    )


def test_parse_never_saves(client):
    r = client.post("/api/finance/parse", json={"text": "lunch 250 cash at Kaldi's"})
    assert r.status_code == 200
    draft = r.json()["draft"]
    assert draft["amount_minor"] == 25000 and draft["kind"] == "expense"
    assert draft["merchant"].startswith("Kaldi")
    assert client.get("/api/finance/transactions").json() == []
    assert client.post("/api/finance/parse", json={"text": "no number here"}).status_code == 400


def test_budget_worked_example_and_alert(client):
    cats = {
        n: _category(client, n)
        for n in ("Rent", "Household & Food", "Transport", "Savings", "Emergency")
    }
    lines = [
        {"category_id": cats["Rent"], "planned": 7500},
        {"category_id": cats["Household & Food"], "planned": 8000},
        {"category_id": cats["Transport"], "planned": 2000},
        {"category_id": cats["Savings"], "planned": 10000},
        {"category_id": cats["Emergency"], "planned": 3000},
    ]
    from datetime import UTC, datetime

    period = f"{datetime.now(UTC):%Y-%m}"
    b = client.post(
        "/api/finance/budgets", json={"period": period, "income_plan": 35000, "lines": lines}
    )
    assert b.status_code == 201, b.text
    assert b.json()["unallocated_minor"] == (35000 - 30500) * 100
    assert (
        client.post("/api/finance/budgets", json={"period": period}).status_code == 409
    )  # one per month

    client.post(
        "/api/finance/transactions", json={"amount": 6900, "category_id": cats["Household & Food"]}
    )
    summary = client.get("/api/finance/summary", params={"period": period}).json()
    food = next(x for x in summary["budget"]["lines"] if x["category"] == "Household & Food")
    assert food["utilisation_pct"] == 86.2 and food["status"] == "amber"
    assert (
        summary["spent_minor"] == 690000 and summary["left_in_budget_minor"] == (30500 - 6900) * 100
    )
    alerts = client.get("/api/finance/alerts").json()
    assert [a["category"] for a in alerts["budget"]] == ["Household & Food"]
    client.post(
        "/api/finance/transactions", json={"amount": 2000, "category_id": cats["Household & Food"]}
    )
    food = next(
        x
        for x in client.get("/api/finance/summary").json()["budget"]["lines"]
        if x["category"] == "Household & Food"
    )
    assert food["status"] == "red" and food["overspend_minor"] == 90000

    nxt = (datetime.now(UTC).replace(day=1) + timedelta(days=32)).strftime("%Y-%m")
    copied = client.post(f"/api/finance/budgets/{b.json()['id']}/copy", json={"period": nxt})
    assert copied.status_code == 201 and len(copied.json()["lines"]) == 5


def test_recurring_bill_settle_partial_and_versioning(client):
    from datetime import UTC, datetime

    today = datetime.now(UTC).date()
    rent = client.post(
        "/api/finance/recurring",
        json={
            "kind": "bill",
            "title": "Rent",
            "amount": 7500,
            "rule": {"freq": "monthly", "start": today.isoformat()},
        },
    )
    assert rent.status_code == 201, rent.text
    rule = rent.json()
    occ = client.get(
        "/api/finance/occurrences",
        params={"from": today.isoformat(), "to": (today + timedelta(days=95)).isoformat()},
    ).json()
    assert len(occ) >= 3  # generated ahead, once each
    again = client.get(
        "/api/finance/occurrences",
        params={"from": today.isoformat(), "to": (today + timedelta(days=95)).isoformat()},
    ).json()
    assert [o["id"] for o in again] == [o["id"] for o in occ]  # idempotent

    first = occ[0]
    part = client.post(
        f"/api/finance/occurrences/{first['id']}/settle", json={"status": "partial", "amount": 3000}
    )
    assert part.status_code == 200, part.text
    assert part.json()["occurrence"]["remaining_minor"] == 450000
    done = client.post(f"/api/finance/occurrences/{first['id']}/settle", json={})
    assert done.json()["occurrence"]["status"] == "paid"
    assert client.post(f"/api/finance/occurrences/{first['id']}/settle", json={}).status_code == 409
    paid = [
        t
        for t in client.get("/api/finance/transactions").json()
        if t["occurrence_id"] == first["id"]
    ]
    assert sum(t["amount_minor"] for t in paid) == 750000

    # Editing creates a new version from the next occurrence; the settled one is untouched.
    changed = client.patch(f"/api/finance/recurring/{rule['id']}", json={"amount": 8000})
    assert changed.status_code == 200 and changed.json()["version"] == 2
    after = client.get(
        "/api/finance/occurrences",
        params={"from": today.isoformat(), "to": (today + timedelta(days=95)).isoformat()},
    ).json()
    assert next(o for o in after if o["id"] == first["id"])["expected_minor"] == 750000
    assert all(o["expected_minor"] == 800000 for o in after if o["status"] == "expected")
    assert len(client.get("/api/finance/recurring").json()) == 1  # only the active version


def test_transfer_two_legs_balances_and_soft_delete(client):
    wallet = client.get("/api/finance/accounts").json()[0]
    bank = client.post("/api/finance/accounts", json={"name": "CBE", "type": "bank"}).json()
    assert client.post("/api/finance/accounts", json={"name": "CBE"}).status_code == 409
    client.post(
        "/api/finance/transactions",
        json={"kind": "income", "amount": 1000, "account_id": wallet["id"]},
    )
    t = client.post(
        "/api/finance/transactions",
        json={
            "kind": "transfer",
            "amount": 400,
            "account_id": wallet["id"],
            "to_account_id": bank["id"],
        },
    )
    assert t.status_code == 201 and len(t.json()) == 2
    balances = {a["name"]: a["balance_minor"] for a in client.get("/api/finance/accounts").json()}
    assert balances == {"Cash wallet": 60000, "CBE": 40000}
    assert client.delete(f"/api/finance/transactions/{t.json()[0]['id']}").status_code == 204
    balances = {a["name"]: a["balance_minor"] for a in client.get("/api/finance/accounts").json()}
    assert balances == {"Cash wallet": 100000, "CBE": 0}


def test_savings_goal_projection(client):
    goal = client.post(
        "/api/finance/savings-goals",
        json={"name": "Laptop", "target": 30000, "monthly_contribution": 5000},
    )
    assert goal.status_code == 201, goal.text
    client.post(
        f"/api/finance/savings-goals/{goal.json()['id']}/contributions", json={"amount": 5000}
    )
    g = client.get("/api/finance/savings-goals").json()[0]
    assert g["saved_minor"] == 500000 and g["progress_pct"] == 16.7 and g["projected_completion"]


def test_agent_money_tools_need_approval_and_are_never_auto_allowed(tmp_path):
    from personal_agent.app.container import build_app
    from personal_agent.config.settings import Settings

    app = build_app(
        settings=Settings.from_env(
            {"PERSONAL_AGENT_PROVIDER": "fake", "DATABASE_URL": f"sqlite:///{tmp_path / 'a.db'}"}
        )
    )
    specs = {s.name: s for s in app.registry.specs()}
    assert specs["finance_record_transaction"].access_kind == "financial"
    assert specs["finance_delete_transaction"].access_kind == "destructive"
    assert specs["finance_summary"].access_kind == "read"
    from personal_agent.application.security.owner_policy import OwnerPermissionPolicy
    from personal_agent.application.security.permissions import DEFAULT_POLICY

    assert DEFAULT_POLICY.approval_required(specs["finance_record_transaction"])
    policy = OwnerPermissionPolicy(
        modes_of=lambda: {"finance_record_transaction": "allow"},
        autonomy_preset_of=lambda: "balanced",
    )
    assert policy.approval_required(specs["finance_record_transaction"])  # Allow is ignored
    assert not DEFAULT_POLICY.approval_required(specs["finance_query"])


# -- recurring tasks and strict bodies ---------------------------------------------------


def test_recurring_task_spawns_next_occurrence_once(client):
    made = client.post(
        "/api/tasks",
        json={
            "title": "Weekly report",
            "recurrence": {"freq": "weekly"},
            "plan_date": "2026-11-02",
        },
    )
    assert made.status_code == 201, made.text
    task = made.json()
    assert task["recurrence"]["freq"] == "weekly"
    done = client.post(f"/api/tasks/{task['id']}/complete", json={"outcome": "achieved"})
    assert done.status_code == 200, done.text
    after = client.get("/api/tasks", params={"from": "2026-11-03", "to": "2026-12-31"}).json()
    nxt = [t for t in after if t["title"] == "Weekly report"]
    assert [t["plan_date"] for t in nxt] == ["2026-11-09"]
    assert nxt[0]["status"] == "planned" and nxt[0]["recurrence"]["freq"] == "weekly"
    # Finishing the new one moves the chain on again; the first is not duplicated.
    client.post(f"/api/tasks/{nxt[0]['id']}/complete", json={"outcome": "achieved"})
    later = client.get("/api/tasks", params={"from": "2026-11-03", "to": "2026-12-31"}).json()
    assert sorted(t["plan_date"] for t in later if t["title"] == "Weekly report") == [
        "2026-11-09",
        "2026-11-16",
    ]


def test_unknown_task_fields_are_rejected_not_dropped(client):
    r = client.post("/api/tasks", json={"title": "x", "recurence": "weekly"})
    assert r.status_code == 422
    bad = client.post("/api/tasks", json={"title": "x", "recurrence": {"freq": "hourly"}})
    assert bad.status_code == 400
    task = client.post("/api/tasks", json={"title": "x", "recurrence": {"freq": "daily"}}).json()
    cleared = client.patch(f"/api/tasks/{task['id']}", json={"recurrence": None})
    assert cleared.status_code == 200 and cleared.json()["recurrence"] is None


# -- proactive nudges --------------------------------------------------------------------


def test_nudges_are_factual_and_quiet_when_calm(tmp_path):
    from datetime import UTC, datetime

    from personal_agent.app.container import build_app
    from personal_agent.config.settings import Settings

    app = build_app(
        settings=Settings.from_env(
            {"PERSONAL_AGENT_PROVIDER": "fake", "DATABASE_URL": f"sqlite:///{tmp_path / 'n.db'}"}
        )
    )
    owner = "dashboard"
    assert app.habits.nudge_text(owner) is None
    assert app.finance.nudge_text(owner) is None
    app.habits.create(owner, {"name": "Exercise", "rule": {"freq": "daily"}})
    assert "Exercise" in (app.habits.nudge_text(owner) or "")
    cats = {c["name"]: c["id"] for c in app.finance.categories(owner)}
    period = f"{datetime.now(UTC):%Y-%m}"
    app.finance.create_budget(
        owner,
        {"period": period, "lines": [{"category_id": cats["Transport"], "planned": 1000}]},
    )
    app.finance.record(owner, {"amount": 900, "category_id": cats["Transport"]})
    text = app.finance.nudge_text(owner) or ""
    assert "Transport" in text and "90%" in text


# -- review ------------------------------------------------------------------------------


def test_weekly_review_combines_tasks_habits_and_money(client):
    done = client.post("/api/tasks", json={"title": "Report"}).json()
    client.post(f"/api/tasks/{done['id']}/complete", json={"outcome": "achieved"})
    missed = client.post("/api/tasks", json={"title": "Gym"}).json()
    client.post(
        f"/api/tasks/{missed['id']}/complete", json={"outcome": "missed", "note": "was sick"}
    )
    habit = client.post("/api/habits", json={"name": "Prayer", "rule": {"freq": "daily"}}).json()
    client.post(f"/api/habits/{habit['id']}/checkins", json={"status": "done"})
    client.post("/api/finance/transactions/quick", json={"amount": 120})

    week = client.get("/api/review", params={"period": "week"}).json()
    assert week["tasks"]["planned"] == 2 and week["tasks"]["rate"] == 0.5
    assert week["tasks"]["missed_tasks"][0]["note"] == "was sick"
    assert week["habits"][0]["habit"] == "Prayer" and week["habits"][0]["done"] == 1
    assert week["money"]["spent_minor"] == 12000
    assert client.get("/api/review", params={"period": "month"}).status_code == 200
    assert client.get("/api/review", params={"period": "year"}).status_code == 400


# -- chat thread titles ------------------------------------------------------------------


def test_conversation_list_has_titles_and_hides_empty_threads(client):
    reply = client.post("/api/chat", json={"text": "Plan my week please"}).json()
    listed = client.get("/api/conversations").json()
    mine = [c for c in listed if c["id"] == reply["session_id"]]
    assert mine and mine[0]["title"] == "Plan my week please"
    assert all(c["title"] for c in listed)  # empty conversations are not listed


# -- money overview, payslips, day score (Improvement Plan) --------------------------------


def test_payslip_net_income_and_overview(client):
    today = _iso_today(client)
    bad = client.post(
        "/api/finance/payslips",
        json={"payday": today, "components": {"basic": "1000"}, "deductions": {"pension": "2000"}},
    )
    assert bad.status_code == 400
    r = client.post(
        "/api/finance/payslips",
        json={
            "payday": today,
            "components": {"basic": "10000", "allowance": "2000"},
            "deductions": {"income_tax": "1500", "pension": "700"},
            "record_income": True,
        },
    )
    assert r.status_code == 201, r.text
    slip = r.json()
    assert slip["gross_minor"] == 1_200_000 and slip["net_minor"] == 980_000
    assert slip["shares"]["basic"] == 83.3

    # Saving the same pay period again updates it and does not log income twice.
    again = client.post(
        "/api/finance/payslips",
        json={
            "payday": today,
            "components": {"basic": "10000", "allowance": "2000"},
            "deductions": {"income_tax": "1500", "pension": "700"},
            "record_income": True,
        },
    )
    assert again.status_code == 201
    assert len(client.get("/api/finance/payslips").json()["items"]) == 1

    client.post("/api/finance/transactions/quick", json={"amount": "250"})
    month = client.get("/api/finance/overview?range=month").json()
    assert month["income_minor"] == 980_000
    assert month["spent_minor"] == 25_000
    assert month["net_minor"] == 955_000
    assert month["categories"] == [] or month["categories"][0]["share_pct"] == 100.0
    assert client.get("/api/finance/overview?range=today").json()["spent_minor"] == 25_000
    nxt = client.get("/api/finance/overview?range=next_month").json()
    assert nxt["forecast"]["expected_income_minor"] == 980_000
    assert client.get("/api/finance/overview?range=custom").status_code == 400
    assert client.get("/api/finance/overview?range=nope").status_code == 400
    assert client.get("/api/finance/budget-suggestion").json()["split"]["savings"] == 196_000


def test_day_score_on_today_and_endpoint(client):
    habit = client.post("/api/habits", json={"name": "Prayer", "rule": {"freq": "daily"}}).json()
    client.post(f"/api/habits/{habit['id']}/checkins", json={"status": "done"})
    score = client.get("/api/score/today").json()
    habits = next(a for a in score["areas"] if a["area"] == "habits")
    assert habits["ratio"] == 1.0
    assert score["total"] is not None
    assert client.get("/api/today").json()["score"]["total"] == score["total"]
    assert client.get("/api/score/today?rest=true").json()["total"] is None
    assert len(client.get("/api/score/week").json()["days"]) == 7


def test_month_close_insights_and_csv(client):
    client.post("/api/finance/transactions/quick", json={"amount": "300"})
    client.post(
        "/api/finance/transactions",
        json={"kind": "income", "amount": "5000", "merchant": "=cmd()"},
    )
    close = client.get("/api/finance/close").json()
    assert close["income_minor"] == 500_000 and close["spent_minor"] == 30_000
    assert len(close["uncategorised"]) >= 1
    assert "income" in close["summary"] and close["rollover_proposal"] is None
    assert client.get("/api/finance/close?period=bad").status_code == 400
    assert isinstance(client.get("/api/finance/insights").json()["items"], list)
    csv = client.get("/api/finance/export.csv")
    assert csv.status_code == 200 and csv.text.startswith("date,kind,amount")
    assert "'=cmd()" in csv.text  # formula text is neutralised


def test_today_evening_block_and_inbox_extras(client):
    today = client.get("/api/today").json()
    assert set(today["evening"]) >= {"active", "carry_over", "tomorrow", "diary_prompt"}
    assert isinstance(today["agent_did"], list)
    bulk = client.post("/api/approvals/bulk-approve")
    assert bulk.status_code == 200 and bulk.json() == {"approved": [], "skipped": 0}
    assert "retention_pct" in client.get("/api/learn/stats").json()
