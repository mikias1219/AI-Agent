"""Composition root: builds the one, wired object graph for the whole app.

The only file in the project that "knows everything." Every interface (CLI now,
REST/Telegram later) starts by asking for `get_app()` or building a custom container
in tests with seeded provider scripts. Swapping `ollama` ↔ `fake` is a Settings flip.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from personal_agent.config import Settings, load_settings
from personal_agent.core.agent import Agent
from personal_agent.core.ports import (
    ConversationRepository,
    MemoryStore,
    TaskRepository,
    ToolRegistry,
)
from personal_agent.logging_setup import configure_logging
from personal_agent.memory.sqlite_memory import SqliteMemoryStore
from personal_agent.providers.base import ProviderConfig
from personal_agent.providers.fake import FakeProvider
from personal_agent.providers.ollama import OllamaProvider
from personal_agent.security.approvals import ApprovalGatewayImpl
from personal_agent.security.permissions import DEFAULT_POLICY
from personal_agent.services.chat_service import ChatService
from personal_agent.services.task_service import TaskService
from personal_agent.storage.db import create_engine_from_url, init_db, make_session_factory
from personal_agent.storage.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
    ConversationRepositoryImpl,
    TaskRepositoryImpl,
)
from personal_agent.tools.builtins.utility import get_current_datetime, noop
from personal_agent.tools.registry import ToolRegistryImpl

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContainer:
    """Everything an interface needs, cleanly typed by repository/tool contracts."""

    settings: Settings
    agent: Agent
    chat: ChatService
    tasks: TaskService
    conversations: ConversationRepository
    tasks_repository: TaskRepository
    memory: MemoryStore
    registry: ToolRegistry


def build_app(
    *,
    settings: Settings | None = None,
    approval_notifier=None,
    provider=None,
) -> AppContainer:
    """Wire a complete app; tests pass `settings`, `provider`, `notifier` overrides."""
    settings = settings or load_settings()
    configure_logging(settings)
    logger.info(
        "Building app: provider=%s db=%s model=%s.",
        settings.provider,
        settings.database_url.split("///")[-1],
        settings.ollama_model if settings.provider == "ollama" else "(fake)",
    )

    # -- storage ------------------------------------------------------------
    engine = create_engine_from_url(settings.database_url)
    init_db(engine)
    factory = make_session_factory(engine)

    conversations = ConversationRepositoryImpl(factory)
    task_repository = TaskRepositoryImpl(factory)
    memory_store = SqliteMemoryStore(factory)

    # -- security & tools ---------------------------------------------------
    notifier = approval_notifier
    approvals_repo = ApprovalRepositoryImpl(factory)
    audit_log = AuditLogImpl(factory)
    approval_gateway = ApprovalGatewayImpl(
        repo=approvals_repo,
        audit=audit_log,
        notifier=notifier,
    )
    policy = DEFAULT_POLICY

    registry = ToolRegistryImpl(
        policy=policy,
        approvals=approval_gateway,
        audit=audit_log,
    )
    registry.register_all([get_current_datetime, noop])

    # -- model provider ------------------------------------------------------
    if provider is not None:
        model_provider = provider
    elif settings.provider == "ollama":
        model_provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            config=ProviderConfig(model_name=settings.ollama_model),
        )
    else:  # offline-friendly default
        model_provider = FakeProvider()

    # -- agent & services ----------------------------------------------------
    agent = Agent(provider=model_provider, registry=registry)
    chat = ChatService(
        agent=agent,
        conversations=conversations,
        memory=memory_store,
        history_limit=settings.history_limit,
    )
    tasks = TaskService(task_repository)

    return AppContainer(
        settings=settings,
        agent=agent,
        chat=chat,
        tasks=tasks,
        conversations=conversations,
        tasks_repository=task_repository,
        memory=memory_store,
        registry=registry,
    )


_app: AppContainer | None = None


def get_app(**build_kwargs) -> AppContainer:
    """Process-lifetime singleton app; tests pass build kwargs for fresh graphs."""
    global _app
    if _app is None or build_kwargs:
        _app = build_app(**build_kwargs)
    return _app


def reset_app() -> None:
    """Drop the cached container (mainly for test isolation)."""
    global _app
    _app = None
