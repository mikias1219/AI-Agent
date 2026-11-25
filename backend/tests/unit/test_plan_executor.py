"""Plan executor: ordered runs, pause at commit steps, resume after approval, execute once."""

from __future__ import annotations

import pytest

from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.services.approval_service import ApprovalService
from personal_agent.application.services.plan_executor import PlanExecutor
from personal_agent.application.services.plan_service import PlanService
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import ToolSpec
from personal_agent.infrastructure.persistence.goal_store import (
    GoalRepositoryImpl,
    PlanRepositoryImpl,
)
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
)

OWNER = "dashboard"


class Harness:
    def __init__(self, session_factory, *, paused: bool = False) -> None:
        self.calls: list[tuple[str, dict]] = []
        audit = AuditLogImpl(session_factory)
        self.approvals_repo = ApprovalRepositoryImpl(session_factory)
        self.registry = ToolRegistryImpl(
            policy=PermissionPolicy(),
            approvals=ApprovalGatewayImpl(repo=self.approvals_repo, audit=audit, durable=True),
            audit=audit,
            is_paused=lambda _ctx: paused,
        )
        for name, kind, untrusted in (
            ("read_a", "read", True),
            ("draft_b", "prepare", False),
            ("send_c", "execute", False),
            ("read_d", "read", False),
        ):
            self.registry.register(self._tool(name, kind, untrusted))
        self.approval_service = ApprovalService(
            store=self.approvals_repo, registry=self.registry, audit=audit
        )
        plan_repo = PlanRepositoryImpl(session_factory)
        self.executor = PlanExecutor(plan_repo, self.registry, approvals=self.approvals_repo.get)
        self.approval_service.add_listener(self.executor.on_approval)
        kinds = {s.name: s.access_kind for s in self.registry.specs()}
        self.plans = PlanService(
            plan_repo,
            GoalRepositoryImpl(session_factory),
            access_kind_of=kinds.get,
            after_approve=lambda pid, owner: self.executor.run_authorized(pid, owner),
        )

    def _tool(self, name: str, kind: str, untrusted: bool) -> ToolSpec:
        def handler(_ctx, args) -> str:
            self.calls.append((name, dict(args)))
            return f"out:{name}"

        return ToolSpec(
            name,
            name,
            {"type": "object", "properties": {"x": {"type": "string"}}},
            kind,  # type: ignore[arg-type]
            handler,
            untrusted_output=untrusted,
        )

    def propose(self, steps):
        return self.plans.propose(OWNER, "p", steps)

    @property
    def names(self) -> list[str]:
        return [n for n, _ in self.calls]


@pytest.fixture()
def h(session_factory) -> Harness:
    return Harness(session_factory)


def test_runs_authorized_steps_in_order_with_arguments(h: Harness) -> None:
    plan = h.propose(
        [
            {"id": "s1", "title": "r", "tool_name": "read_a", "arguments": {"x": "1"}},
            {"id": "s2", "title": "d", "tool_name": "draft_b", "depends_on": ["s1"]},
        ]
    )
    done = h.plans.approve(plan.id, OWNER)
    assert h.calls == [("read_a", {"x": "1"}), ("draft_b", {})]
    assert [s.status for s in done.steps] == ["done", "done"]
    assert done.status == "done"
    assert done.steps[0].result.startswith("[UNTRUSTED_EXTERNAL_CONTENT] out:read_a")
    assert done.steps[1].result == "out:draft_b"


def test_pauses_at_commit_step_then_resumes_after_approval(h: Harness) -> None:
    plan = h.propose(
        [
            {"id": "s1", "title": "r", "tool_name": "read_a"},
            {"id": "s2", "title": "send", "tool_name": "send_c", "arguments": {"x": "hi"}},
            {"id": "s3", "title": "after", "tool_name": "read_d"},
        ]
    )
    paused = h.plans.approve(plan.id, OWNER)
    assert h.names == ["read_a"]  # commit not run, later step held back
    assert [s.status for s in paused.steps] == ["done", "needs_ok", "planned"]
    assert paused.status == "approved"
    approval_id = paused.steps[1].approval_id
    assert approval_id
    approval = h.approvals_repo.get(approval_id)
    assert approval is not None and approval.status.value == "pending"
    assert approval.untrusted_content is True  # BR-04: read_a output tainted the run

    # Re-running while still pending neither re-executes nor duplicates the approval.
    h.plans.resume(plan.id, OWNER)
    assert h.names == ["read_a"]
    assert len(h.approval_service.list_approvals(None, limit=10)) == 1

    h.approval_service.decide(approval_id, True, actor=OWNER, channel="dashboard")
    final = h.plans.get(plan.id, OWNER)
    assert h.names == ["read_a", "send_c", "read_d"]
    assert h.calls[1] == ("send_c", {"x": "hi"})
    assert [s.status for s in final.steps] == ["done", "done", "done"]
    assert final.status == "done"

    # Execute once: further resumes or repeated decisions never run anything again.
    with pytest.raises(Exception, match="approved plan"):
        h.plans.resume(plan.id, OWNER)
    h.approval_service.decide(approval_id, True, actor=OWNER, channel="dashboard")
    assert h.names.count("send_c") == 1


def test_denied_commit_step_fails_plan_and_never_runs(h: Harness) -> None:
    plan = h.propose(
        [
            {"id": "s1", "title": "send", "tool_name": "send_c"},
            {"id": "s2", "title": "after", "tool_name": "read_d"},
        ]
    )
    paused = h.plans.approve(plan.id, OWNER)
    h.approval_service.decide(
        paused.steps[0].approval_id or "", False, actor=OWNER, channel="dashboard"
    )
    final = h.plans.get(plan.id, OWNER)
    assert [s.status for s in final.steps] == ["failed", "planned"]
    assert h.calls == []
    assert final.status == "approved"


def test_failed_step_stops_the_plan(h: Harness) -> None:
    plan = h.propose(
        [
            {"id": "s1", "title": "bad", "tool_name": "read_a", "arguments": {"x": 5}},
            {"id": "s2", "title": "after", "tool_name": "read_d"},
        ]
    )
    done = h.plans.approve(plan.id, OWNER)
    assert [s.status for s in done.steps] == ["failed", "planned"]
    assert "Bad arguments" in done.steps[0].result
    assert h.calls == []


def test_running_step_is_never_rerun_after_a_crash(h: Harness) -> None:
    plan = h.propose([{"id": "s1", "title": "r", "tool_name": "read_a"}])
    h.plans.approve(plan.id, OWNER)  # runs once
    stored = h.plans.get(plan.id, OWNER)
    assert stored.status == "done"

    plan2 = h.propose([{"id": "s1", "title": "r", "tool_name": "draft_b"}])
    repo = PlanRepositoryImpl(h.plans._repository._factory)  # noqa: SLF001
    loaded = repo.get(plan2.id)
    assert loaded is not None
    loaded.status = "approved"
    loaded.steps[0].status = "running"  # simulate a crash mid-step
    repo.save(loaded)
    after = h.executor.run_authorized(plan2.id, OWNER)
    assert after.steps[0].status == "failed"
    assert h.names == ["read_a"]


def test_paused_agent_blocks_plan_commit_and_prepare(session_factory) -> None:
    h = Harness(session_factory, paused=True)
    plan = h.propose([{"id": "s1", "title": "d", "tool_name": "draft_b"}])
    done = h.plans.approve(plan.id, OWNER)
    assert done.steps[0].status == "failed"
    assert h.calls == []
