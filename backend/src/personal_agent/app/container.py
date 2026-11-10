"""Composition root: builds the one, wired object graph for the whole app.

The only file in the project that "knows everything." Every interface (CLI, dashboard,
Telegram) starts by asking for `get_app()` or building a custom container in tests with
seeded provider scripts. Swapping `ollama` ↔ `fake` is a Settings flip.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from personal_agent.application.agent import Agent
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import DEFAULT_POLICY
from personal_agent.application.services.auth_service import WorkspaceAuthService
from personal_agent.application.services.chat_service import ChatService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.services.telegram_service import TelegramService
from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.config.logging import configure_logging
from personal_agent.config.settings import Settings, load_settings
from personal_agent.domain.ports import (
    ApprovalGateway,
    ConversationRepository,
    MemoryStore,
    TaskRepository,
    ToolRegistry,
)
from personal_agent.infrastructure.integrations.telegram.client import TelegramBotClient
from personal_agent.infrastructure.integrations.telegram.runner import (
    TelegramBotRunner,
    build_allowed_chats,
)
from personal_agent.infrastructure.integrations.telegram.worker import TelegramWorker
from personal_agent.infrastructure.model_providers.base import ProviderConfig
from personal_agent.infrastructure.model_providers.fake_provider import (
    CLOUD_OFFLINE_REPLY,
    FakeProvider,
)
from personal_agent.infrastructure.model_providers.hermes_agent import HermesAgent
from personal_agent.infrastructure.model_providers.ollama_provider import OllamaProvider
from personal_agent.infrastructure.model_providers.openai_compatible import (
    OpenAICompatibleProvider,
)
from personal_agent.infrastructure.model_providers.runtime_selection import (
    RuntimeChoice,
    select_inference_runtime,
)
from personal_agent.infrastructure.model_providers.setup_status import ModelSetupStatus
from personal_agent.infrastructure.persistence.account_repository import (
    WorkspaceAccountRepositoryImpl,
)
from personal_agent.infrastructure.persistence.database import (
    create_engine_from_url,
    init_db,
    make_session_factory,
)
from personal_agent.infrastructure.persistence.hub_store import (
    GoogleConnectionStore,
    HubStore,
)
from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore
from personal_agent.infrastructure.persistence.repositories import (
    ApprovalRepositoryImpl,
    AuditLogImpl,
    ConversationRepositoryImpl,
    TaskRepositoryImpl,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class AppContainer:
    """Everything an interface needs, cleanly typed by repository/tool contracts."""

    settings: Settings
    model_setup: ModelSetupStatus
    runtime: RuntimeChoice
    auth: WorkspaceAuthService
    telegram: TelegramService
    telegram_worker: TelegramWorker | None
    agent: Agent | HermesAgent
    chat: ChatService
    tasks: TaskService
    conversations: ConversationRepository
    tasks_repository: TaskRepository
    memory: MemoryStore
    registry: ToolRegistry
    audit: AuditLogImpl
    approvals: ApprovalGateway
    approvals_repository: ApprovalRepositoryImpl
    hub: HubStore
    google: GoogleConnectionStore


def build_app(
    *,
    settings: Settings | None = None,
    approval_notifier=None,
    provider=None,
) -> AppContainer:
    """Wire a complete app; tests pass `settings`, `provider`, `notifier` overrides."""
    settings = settings or load_settings()
    configure_logging(settings)
    runtime = select_inference_runtime(settings)
    from urllib.parse import urlsplit

    db = urlsplit(settings.database_url)
    db_label = (
        "sqlite"
        if db.scheme.startswith("sqlite")
        else f"{db.scheme.split('+')[0]}://{db.hostname or 'db'}"
    )
    logger.info(
        "Building app: provider=%s runtime=%s db=%s model=%s.",
        settings.provider,
        runtime.active_runtime,
        db_label,
        settings.ollama_model if settings.provider in ("ollama", "hermes") else "(fake)",
    )
    if runtime.reason:
        logger.info("Inference runtime reason: %s", runtime.reason)

    # -- storage ------------------------------------------------------------
    engine = create_engine_from_url(settings.database_url)
    init_db(engine)
    factory = make_session_factory(engine)

    conversations = ConversationRepositoryImpl(factory)
    task_repository = TaskRepositoryImpl(factory)
    memory_store = SqliteMemoryStore(factory)

    # -- security & tools ---------------------------------------------------
    auditlog = AuditLogImpl(factory)
    approvals_repo = ApprovalRepositoryImpl(factory)
    approval_gateway = ApprovalGatewayImpl(
        repo=approvals_repo,
        audit=auditlog,
        notifier=approval_notifier,
    )
    policy = DEFAULT_POLICY

    registry = ToolRegistryImpl(
        policy=policy,
        approvals=approval_gateway,
        audit=auditlog,
    )
    registry.register_all([get_current_datetime])

    # -- model provider / agent ---------------------------------------------
    if provider is not None:
        model_provider = provider
        agent: Agent | HermesAgent = Agent(provider=model_provider, registry=registry)
        runtime = RuntimeChoice(
            active_runtime="fake" if settings.provider == "fake" else "ollama_agent",
            reason="Test provider override",
            use_hermes=False,
        )
    elif runtime.use_hermes:
        agent = HermesAgent(settings=settings, registry=registry)
    elif settings.provider == "fake":
        # Production cloud has no Ollama; explain instead of a bare "Okay."
        fake = (
            FakeProvider(default_content=CLOUD_OFFLINE_REPLY)
            if settings.environment == "production"
            else FakeProvider()
        )
        agent = Agent(provider=fake, registry=registry)
    elif settings.provider == "openai":
        agent = Agent(
            provider=OpenAICompatibleProvider(
                base_url=settings.openai_compat_base_url,
                api_key=settings.openai_compat_api_key,
                config=ProviderConfig(
                    model_name=settings.openai_compat_model,
                    timeout_seconds=settings.openai_compat_timeout_seconds,
                    max_turn_retries=2,
                    max_output_tokens=settings.openai_compat_max_output_tokens,
                ),
            ),
            registry=registry,
        )
    else:
        agent = Agent(
            provider=OllamaProvider(
                base_url=settings.ollama_base_url,
                config=ProviderConfig(
                    model_name=settings.ollama_model,
                    timeout_seconds=settings.ollama_timeout_seconds,
                    max_turn_retries=1,
                    context_tokens=settings.ollama_context_tokens,
                    max_output_tokens=settings.ollama_max_output_tokens,
                    keep_alive=settings.ollama_keep_alive,
                ),
            ),
            registry=registry,
        )
    chat = ChatService(
        agent=agent,
        conversations=conversations,
        memory=memory_store,
        audit=auditlog,
        history_limit=settings.history_limit,
    )
    tasks = TaskService(task_repository, audit=auditlog)
    registry.register_all(task_tools(tasks))

    telegram_client = (
        TelegramBotClient(settings.telegram_bot_token) if settings.telegram_bot_token else None
    )
    telegram_worker = (
        TelegramWorker(
            TelegramBotRunner(
                client=telegram_client,
                chat_service=chat,
                audit=auditlog,
                allowed_chat_ids=build_allowed_chats(settings.telegram_allowed_chat_ids),
            )
        )
        if telegram_client
        else None
    )

    return AppContainer(
        settings=settings,
        model_setup=ModelSetupStatus(),
        runtime=runtime,
        auth=WorkspaceAuthService(
            WorkspaceAccountRepositoryImpl(factory), settings.dashboard_password_hash
        ),
        telegram=TelegramService(telegram_client),
        telegram_worker=telegram_worker,
        agent=agent,
        chat=chat,
        tasks=tasks,
        conversations=conversations,
        tasks_repository=task_repository,
        memory=memory_store,
        registry=registry,
        audit=auditlog,
        approvals=approval_gateway,
        approvals_repository=approvals_repo,
        hub=HubStore(factory),
        google=GoogleConnectionStore(factory, secret_key=settings.dashboard_secret_key),
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
