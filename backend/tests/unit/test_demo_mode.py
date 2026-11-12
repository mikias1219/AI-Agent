"""Demo workspace isolation and SIMULATED tools (UX-12)."""

from __future__ import annotations

from personal_agent.app.container import build_demo_settings, get_demo_app, reset_app
from personal_agent.application.demo.simulate import wrap_tools_as_simulated
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.config.settings import Settings
from personal_agent.domain.models import ToolContext
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
)
from tests.conftest import make_spy_tool


def test_demo_settings_use_separate_database():
    base = Settings()
    base.database_url = "sqlite:///./data/agent.db"
    base.demo_database_url = "sqlite:///./data/demo.db"
    demo = build_demo_settings(base)
    assert demo.database_url == base.demo_database_url
    assert demo.database_url != base.database_url
    assert demo.provider == "fake"


def test_wrap_tools_as_simulated_never_calls_handler(session_factory):
    audit = AuditLogImpl(session_factory)
    registry = ToolRegistryImpl(
        policy=PermissionPolicy(),
        approvals=ApprovalGatewayImpl(repo=ApprovalRepositoryImpl(session_factory), audit=audit),
        audit=audit,
    )
    calls: list[dict] = []

    def handler(_ctx, args):  # noqa: ANN001
        calls.append(dict(args))
        return "real-send"

    spy = make_spy_tool("email_send", access_kind="execute")
    registry.register(
        spy.__class__(
            name="email_send",
            description=spy.description,
            parameters_schema=spy.parameters_schema,
            access_kind="execute",
            handler=handler,
        )
    )
    assert wrap_tools_as_simulated(registry) == 1
    spec = next(s for s in registry.specs() if s.name == "email_send")
    output = spec.handler(ToolContext(user_id="demo", session_id="s", origin="demo"), {"to": "a"})
    assert output.startswith("SIMULATED:")
    assert calls == []


def test_get_demo_app_seeds_tasks(tmp_path):
    reset_app()
    settings = Settings()
    settings.dashboard_secret_key = "x" * 40
    settings.database_url = f"sqlite:///{tmp_path / 'owner.db'}"
    settings.demo_database_url = f"sqlite:///{tmp_path / 'demo.db'}"
    demo = get_demo_app(settings=settings, force_rebuild=True)
    tasks = demo.tasks.list(owner_user_id="demo")
    assert len(tasks) >= 3
    memories = demo.memories.list("demo")
    assert len(memories) >= 2
    reset_app()
