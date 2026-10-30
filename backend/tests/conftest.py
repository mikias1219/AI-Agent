"""Shared pytest fixtures for the whole suite.

Everything here runs offline: the fake provider, real SQLite (temp file), and
optional approval notifiers — no Ollama, no network, no API keys.
"""

from __future__ import annotations

import pytest
from sqlalchemy.orm import sessionmaker

from personal_agent.application.agent import Agent
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import PermissionPolicy
from personal_agent.application.services.chat_service import ChatService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.domain.models import ToolContext, ToolSpec
from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider
from personal_agent.infrastructure.persistence.database import (
    create_engine_from_url,
    init_db,
    make_session_factory,
)
from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
    ConversationRepositoryImpl,
    TaskRepositoryImpl,
)


@pytest.fixture()
def session_factory(tmp_path) -> sessionmaker:
    """Real temp-file SQLite; init_db ensures schema for each test."""
    engine = create_engine_from_url(f"sqlite:///{tmp_path / 'agent.db'}")
    init_db(engine)
    return make_session_factory(engine)


@pytest.fixture()
def ctx() -> ToolContext:
    """Standard test tool context: cli origin, one fixed user and session."""
    return ToolContext(user_id="tester", session_id="sess-1", origin="cli")


@pytest.fixture()
def policy() -> PermissionPolicy:
    """Non-secret permissive policy: read/prepare yes, execute needs approval."""
    return PermissionPolicy()


@pytest.fixture()
def audit_log(session_factory) -> AuditLogImpl:
    return AuditLogImpl(session_factory)


@pytest.fixture()
def tool_registry(session_factory, policy, audit_log) -> ToolRegistryImpl:
    """Registry with real approval rows but no notifier: requests are deferred."""
    return ToolRegistryImpl(
        policy=policy,
        approvals=ApprovalGatewayImpl(  # no notifier → deferred → nothing runs
            repo=ApprovalRepositoryImpl(session_factory),
            audit=audit_log,
        ),
        audit=audit_log,
    )


@pytest.fixture()
def scripted_provider() -> FakeProvider:
    """Empty script: pops to the stable default 'Okay.'; add turns per test."""
    return FakeProvider()


@pytest.fixture()
def agent(scripted_provider, tool_registry) -> Agent:
    return Agent(provider=scripted_provider, registry=tool_registry)


@pytest.fixture()
def conversations(session_factory) -> ConversationRepositoryImpl:
    return ConversationRepositoryImpl(session_factory)


@pytest.fixture()
def tasks_repo(session_factory) -> TaskRepositoryImpl:
    return TaskRepositoryImpl(session_factory)


@pytest.fixture()
def memory_store(session_factory) -> SqliteMemoryStore:
    return SqliteMemoryStore(session_factory)


@pytest.fixture()
def chat_service(agent, conversations, session_factory, audit_log) -> ChatService:
    return ChatService(
        agent=agent,
        conversations=conversations,
        memory=SqliteMemoryStore(session_factory),
        audit=audit_log,
        history_limit=10,
    )


@pytest.fixture()
def task_service(tasks_repo, audit_log) -> TaskService:
    return TaskService(tasks_repo, audit=audit_log)


def make_spy_tool(name: str, access_kind: str = "read", output: str | None = None) -> ToolSpec:
    """Build a tool whose handler records invocations into a local list."""
    default_output = output or f"ran {name}"
    calls: list[dict] = []

    def handler(_ctx, args) -> str:  # noqa: ANN001 — spec shape
        calls.append(dict(args))
        return default_output

    return ToolSpec(
        name=name,
        description=f"spy tool {name}",
        parameters_schema={"type": "object", "properties": {}},
        access_kind=access_kind,  # type: ignore[arg-type]
        handler=handler,
    )
