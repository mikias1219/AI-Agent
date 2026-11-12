"""Goals and plans: create, propose, approve (READ/PREPARE only), HTTP API, tools, Today."""

from __future__ import annotations

import base64
import hashlib
import json

import pytest
from fastapi.testclient import TestClient

from personal_agent.app.container import build_app
from personal_agent.application.services.goal_service import GoalService
from personal_agent.application.services.plan_service import PlanService
from personal_agent.application.tools.builtins.goals import goal_tools
from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import StorageError
from personal_agent.domain.goals import (
    GoalError,
    Plan,
    PlanStep,
    approve_plan,
    authorized_steps,
    stricter_access,
)
from personal_agent.domain.models import ToolCall, ToolContext
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.goal_store import (
    GoalRepositoryImpl,
    PlanRepositoryImpl,
)
from personal_agent.presentation.web.app import create_dashboard_app
from tests.conftest import make_spy_tool

OWNER = "dashboard"
PASSWORD = "correct horse battery staple"
SALT = b"goals-test-salt"


@pytest.fixture()
def services(session_factory):
    goal_repo = GoalRepositoryImpl(session_factory)
    kinds = {"read_thing": "read", "draft_thing": "prepare", "send_thing": "execute"}
    goals = GoalService(goal_repo)
    plans = PlanService(PlanRepositoryImpl(session_factory), goal_repo, access_kind_of=kinds.get)
    return goals, plans


# -- domain ----------------------------------------------------------------------


def _step(step_id: str, kind: str, status: str = "planned") -> PlanStep:
    return PlanStep(
        id=step_id, title=step_id, tool_name=None, access_kind=kind, status=status, depends_on=[]
    )


def test_domain_approval_parks_hard_ceilings(services) -> None:
    from datetime import UTC, datetime

    plan = Plan(
        id="p",
        goal_id=None,
        owner_user_id="o",
        steps=[
            _step("a", "read"),
            _step("b", "prepare"),
            _step("c", "execute"),
            _step("d", "destructive"),
        ],
        status="proposed",
    )
    approve_plan(plan, now=datetime.now(UTC))
    assert plan.status == "approved"
    assert [s.status for s in plan.steps] == ["planned", "planned", "needs_ok", "needs_ok"]
    assert [s.id for s in authorized_steps(plan)] == ["a", "b"]


def test_stricter_access_never_downgrades() -> None:
    assert stricter_access("read", "execute") == "execute"
    assert stricter_access("destructive", "read") == "destructive"
    assert stricter_access("prepare", None) == "prepare"


# -- service ---------------------------------------------------------------------


def test_create_goal(services) -> None:
    goals, _ = services
    goal = goals.create(
        OWNER, "  Run a 10k  ", success_criteria=["Finish race", " "], next_step="Pick a schedule"
    )
    assert goal.title == "Run a 10k"
    assert goal.success_criteria == ["Finish race"]
    assert goal.status == "active"
    assert goal.progress == 0.0
    assert goals.get(goal.id, OWNER).next_step == "Pick a schedule"
    assert [g.id for g in goals.active(OWNER)] == [goal.id]
    with pytest.raises(GoalError):
        goals.create(OWNER, "   ")
    with pytest.raises(StorageError):
        goals.get(goal.id, "someone-else")


def test_update_goal_validates(services) -> None:
    goals, _ = services
    goal = goals.create(OWNER, "G")
    updated = goals.update(goal.id, OWNER, progress=0.5, status="paused")
    assert (updated.progress, updated.status) == (0.5, "paused")
    assert goals.active(OWNER) == []
    with pytest.raises(GoalError):
        goals.update(goal.id, OWNER, progress=1.5)
    with pytest.raises(GoalError):
        goals.update(goal.id, OWNER, status="weird")


def test_approve_plan_does_not_bypass_ceilings(services) -> None:
    _, plans = services
    plan = plans.propose(
        OWNER,
        "Tell Sam",
        [
            {"id": "s1", "title": "Look up Sam", "tool_name": "read_thing"},
            {"id": "s2", "title": "Draft", "tool_name": "draft_thing", "depends_on": ["s1"]},
            # The author mislabels an execute tool as read: the registry's kind wins.
            {"id": "s3", "title": "Send", "tool_name": "send_thing", "access_kind": "read"},
        ],
    )
    assert plan.status == "proposed"
    assert plan.steps[2].access_kind == "execute"

    approved = plans.approve(plan.id, OWNER)
    assert approved.status == "approved"
    assert [s.status for s in approved.steps] == ["planned", "planned", "needs_ok"]
    # Persisted, and a second approval cannot flip the ceiling step.
    again = plans.get(plan.id, OWNER)
    assert [s.status for s in again.steps] == ["planned", "planned", "needs_ok"]
    with pytest.raises(GoalError):
        plans.approve(plan.id, OWNER)


def test_approve_reclassifies_with_live_registry(session_factory) -> None:
    goal_repo = GoalRepositoryImpl(session_factory)
    kinds = {"thing": "prepare"}
    plans = PlanService(PlanRepositoryImpl(session_factory), goal_repo, access_kind_of=kinds.get)
    plan = plans.propose(OWNER, "P", [{"title": "Do", "tool_name": "thing"}])
    kinds["thing"] = "destructive"  # tool reclassified after proposing
    approved = plans.approve(plan.id, OWNER)
    assert approved.steps[0].access_kind == "destructive"
    assert approved.steps[0].status == "needs_ok"


def test_propose_rejects_bad_input(services) -> None:
    goals, plans = services
    with pytest.raises(GoalError, match="unknown tool"):
        plans.propose(OWNER, "P", [{"title": "x", "tool_name": "nope"}])
    with pytest.raises(GoalError):
        plans.propose(OWNER, "P", [])
    with pytest.raises(GoalError, match="depends"):
        plans.propose(OWNER, "P", [{"id": "s1", "title": "x", "depends_on": ["s2"]}])
    with pytest.raises(StorageError):
        plans.propose(OWNER, "P", [{"title": "x"}], goal_id="missing")
    goal = goals.create(OWNER, "G")
    with pytest.raises(StorageError):
        plans.propose("other", "P", [{"title": "x"}], goal_id=goal.id)


def test_cancel_plan(services) -> None:
    _, plans = services
    plan = plans.propose(OWNER, "P", [{"title": "x"}])
    assert plans.cancel(plan.id, OWNER).status == "cancelled"
    with pytest.raises(GoalError):
        plans.approve(plan.id, OWNER)


def test_same_step_ids_in_two_plans(services) -> None:
    _, plans = services
    a = plans.propose(OWNER, "A", [{"title": "x"}])
    b = plans.propose(OWNER, "B", [{"title": "y"}])
    assert a.steps[0].id == b.steps[0].id == "s1"
    assert {p.id for p in plans.list(OWNER)} == {a.id, b.id}


# -- tools through the registry ---------------------------------------------------


def test_tools_via_registry(tmp_path) -> None:
    container = _container(tmp_path)
    ctx = ToolContext(user_id=OWNER, session_id="s", origin="dashboard")
    created = container.registry.execute(
        ToolCall(id="c1", name="goal_create", arguments={"title": "Learn Spanish"}), ctx
    )
    assert created.ok and created.result_type == "task"
    assert created.id == container.goals.active(OWNER)[0].id

    proposed = container.registry.execute(
        ToolCall(
            id="c2",
            name="plan_propose",
            arguments={
                "title": "Study",
                "goal_id": created.id,
                "steps": [
                    {"title": "Find a course"},
                    {"title": "Send RSVP", "tool_name": "google_gmail_send"},
                ],
            },
        ),
        ctx,
    )
    assert proposed.ok and proposed.result_type == "plan"
    plan = container.plans.get(str(proposed.id), OWNER)
    assert plan.status == "proposed" and plan.goal_id == created.id
    assert plan.steps[1].access_kind == "execute"
    assert [s["title"] for s in proposed.fields["steps"]] == ["Find a course", "Send RSVP"]

    bad = container.registry.execute(
        ToolCall(
            id="c3",
            name="plan_propose",
            arguments={"title": "x", "steps": [{"title": "y", "tool_name": "nope"}]},
        ),
        ctx,
    )
    assert not bad.ok and "unknown tool" in (bad.error or "")


def test_goal_tools_have_contracts(services) -> None:
    goals, plans = services
    specs = {s.name: s for s in goal_tools(goals, plans)}
    assert specs["goal_create"].access_kind == "prepare"
    assert specs["plan_propose"].access_kind == "prepare"
    assert specs["plan_propose"].result_type == "plan"
    assert all(s.parameters_schema for s in specs.values())


# -- HTTP + Today -----------------------------------------------------------------


def _container(tmp_path):
    digest = base64.urlsafe_b64encode(
        hashlib.pbkdf2_hmac("sha256", PASSWORD.encode(), SALT, 310_000)
    ).decode()
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "fake",
            "DATABASE_URL": f"sqlite:///{tmp_path / 'goals.db'}",
            "DASHBOARD_PASSWORD_HASH": (
                f"{base64.urlsafe_b64encode(SALT).decode().rstrip('=')}${digest.rstrip('=')}"
            ),
            "DASHBOARD_SECRET_KEY": "test-secret-key-at-least-thirty-two-bytes",
        }
    )
    return build_app(settings=settings, provider=FakeProvider())


@pytest.fixture()
def api(tmp_path):
    container = _container(tmp_path)
    frontend = tmp_path / "frontend"
    frontend.mkdir()
    (frontend / "index.html").write_text('<div id="root"></div>')
    client = TestClient(
        create_dashboard_app(container=container, frontend_dir=frontend),
        base_url="http://127.0.0.1",
    )
    assert client.post("/api/login", json={"password": PASSWORD}).status_code == 200
    return client, container


def test_goals_api_crud_and_today(api) -> None:
    client, container = api
    assert client.get("/api/goals").json() == []
    assert container.today.build(OWNER)["goals"] == []

    created = client.post(
        "/api/goals",
        json={"title": "Ship v1", "success_criteria": ["Users sign up"], "next_step": "Write docs"},
    )
    assert created.status_code == 201
    goal = created.json()
    assert goal["status"] == "active" and goal["plans"] == []

    assert client.post("/api/goals", json={"title": "   "}).status_code == 422
    assert client.get("/api/goals/nope").status_code == 404

    patched = client.patch(f"/api/goals/{goal['id']}", json={"progress": 0.4, "status": "paused"})
    assert patched.status_code == 200 and patched.json()["progress"] == 0.4
    assert client.patch(f"/api/goals/{goal['id']}", json={"progress": 9}).status_code in (400, 422)
    assert container.today.build(OWNER)["goals"] == []  # paused goals are not in progress

    client.patch(f"/api/goals/{goal['id']}", json={"status": "active"})
    today_goals = container.today.build(OWNER)["goals"]
    assert [g["title"] for g in today_goals] == ["Ship v1"]
    assert client.get("/api/goals?status=active").json()[0]["id"] == goal["id"]


def test_plans_api_approve_keeps_ceilings(api) -> None:
    client, container = api
    container.registry.register(make_spy_tool("send_thing", "execute"))
    goal = client.post("/api/goals", json={"title": "Tell Sam"}).json()
    created = client.post(
        "/api/plans",
        json={
            "goal_id": goal["id"],
            "title": "Tell Sam",
            "steps": [
                {"id": "s1", "title": "Draft"},
                {"id": "s2", "title": "Send", "tool_name": "send_thing", "access_kind": "read"},
            ],
        },
    )
    assert created.status_code == 201
    plan = created.json()
    assert plan["status"] == "proposed"
    assert plan["steps"][1]["access_kind"] == "execute"

    approved = client.post(f"/api/plans/{plan['id']}/approve")
    assert approved.status_code == 200
    body = approved.json()
    assert body["status"] == "approved"
    assert [s["status"] for s in body["steps"]] == ["planned", "needs_ok"]
    # Nothing was executed and no approval was created for the ceiling step by approving.
    assert container.approval_service.list_approvals(None, limit=10) == []

    assert client.post(f"/api/plans/{plan['id']}/approve").status_code == 409
    detail = client.get(f"/api/goals/{goal['id']}").json()
    assert [p["id"] for p in detail["plans"]] == [plan["id"]]
    assert client.get(f"/api/plans?goal_id={goal['id']}").json()[0]["id"] == plan["id"]
    assert client.get("/api/plans/nope").status_code == 404
    assert client.post("/api/plans/nope/approve").status_code == 404

    cancelled = client.post("/api/plans", json={"title": "Other", "steps": [{"title": "x"}]}).json()
    assert client.post(f"/api/plans/{cancelled['id']}/cancel").json()["status"] == "cancelled"


def test_plan_create_rejects_unknown_tool(api) -> None:
    client, _ = api
    response = client.post(
        "/api/plans", json={"title": "P", "steps": [{"title": "x", "tool_name": "nope"}]}
    )
    assert response.status_code == 422
    assert json.dumps(response.json())
