"""Composition root: builds the one, wired object graph for the whole app.

The only file in the project that "knows everything." Every interface (CLI, dashboard,
Telegram) starts by asking for `get_app()` or building a custom container in tests with
seeded provider scripts. Swapping `ollama` ↔ `fake` is a Settings flip.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from personal_agent.application.agent import Agent
from personal_agent.application.run_events import FanoutSink, RunEventBroker, RunStepRecorder
from personal_agent.application.security.approvals import ApprovalGatewayImpl
from personal_agent.application.security.permissions import DEFAULT_POLICY
from personal_agent.application.services.approval_service import ApprovalService
from personal_agent.application.services.auth_service import WorkspaceAuthService
from personal_agent.application.services.chat_service import ChatService
from personal_agent.application.services.memory_service import MemoryService
from personal_agent.application.services.onboarding_service import OnboardingService
from personal_agent.application.services.profile_service import ProfileService
from personal_agent.application.services.run_service import RunService
from personal_agent.application.services.scheduler_service import SchedulerService
from personal_agent.application.services.task_service import TaskService
from personal_agent.application.services.telegram_activity import list_telegram_audit_activity
from personal_agent.application.services.telegram_service import TelegramService
from personal_agent.application.tools.builtins.google import google_tools
from personal_agent.application.tools.builtins.memory import memory_tools
from personal_agent.application.tools.builtins.tasks import task_tools
from personal_agent.application.tools.builtins.telegram import telegram_tools
from personal_agent.application.tools.builtins.utility import get_current_datetime
from personal_agent.application.tools.builtins.web import web_tools
from personal_agent.application.tools.registry import ToolRegistryImpl
from personal_agent.config.logging import configure_logging
from personal_agent.config.settings import Settings, load_settings
from personal_agent.domain.ports import (
    AgentRunRepository,
    ApprovalGateway,
    ConversationRepository,
    MemoryStore,
    TaskRepository,
    ToolRegistry,
)
from personal_agent.infrastructure.embeddings.local import LocalHashEmbeddingProvider
from personal_agent.infrastructure.integrations.google.clients import GoogleApiClient
from personal_agent.infrastructure.integrations.google.session import make_access_token_provider
from personal_agent.infrastructure.integrations.mcp.adapter import McpToolAdapter
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
from personal_agent.infrastructure.observability.run_tracing import TracingEventSink
from personal_agent.infrastructure.observability.tracing import build_tracer
from personal_agent.infrastructure.persistence.account_repository import (
    WorkspaceAccountRepositoryImpl,
)
from personal_agent.infrastructure.persistence.database import (
    create_engine_from_url,
    init_db,
    make_session_factory,
)
from personal_agent.infrastructure.persistence.google_connection_store import (
    GoogleConnectionStore,
)
from personal_agent.infrastructure.persistence.job_queue import SqlJobQueue
from personal_agent.infrastructure.persistence.mcp_store import McpServerStoreImpl
from personal_agent.infrastructure.persistence.memory_store import SqliteMemoryStore
from personal_agent.infrastructure.persistence.repositories import (
    AgentRunRepositoryImpl,
    ApprovalRepositoryImpl,
    AuditLogImpl,
    ConversationRepositoryImpl,
    OwnerProfileRepositoryImpl,
    TaskRepositoryImpl,
)
from personal_agent.infrastructure.persistence.scheduler_store import (
    AutomationStoreImpl,
    ReminderStoreImpl,
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
    runs: RunService
    runs_repository: AgentRunRepository
    tasks: TaskService
    profiles: ProfileService
    onboarding: OnboardingService
    conversations: ConversationRepository
    tasks_repository: TaskRepository
    memory: MemoryStore
    memories: MemoryService
    registry: ToolRegistry
    audit: AuditLogImpl
    approvals: ApprovalGateway
    approvals_repository: ApprovalRepositoryImpl
    approval_service: ApprovalService
    google: GoogleConnectionStore
    scheduler: SchedulerService
    reminders: ReminderStoreImpl
    automations: AutomationStoreImpl
    mcp_servers: McpServerStoreImpl
    mcp_adapter: McpToolAdapter


def build_app(
    *,
    settings: Settings | None = None,
    approval_notifier=None,
    provider=None,
    clock: Callable[[], datetime] | None = None,
) -> AppContainer:
    """Wire a complete app; tests pass `settings`, `provider`, `notifier`, `clock` overrides.

    Without an interactive `approval_notifier` approvals are durable: the run pauses and the
    owner decides later through `approval_service` (APR-02).
    """
    now = clock or (lambda: datetime.now(UTC))
    settings = settings or load_settings()
    ttl = timedelta(seconds=max(1.0, settings.approval_ttl_seconds))
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
    runs_repository = AgentRunRepositoryImpl(factory)
    run_broker = RunEventBroker()
    tracer = build_tracer(settings.trace_exporter)
    run_events = FanoutSink(
        [RunStepRecorder(runs_repository), run_broker, TracingEventSink(tracer)]
    )
    embeddings = LocalHashEmbeddingProvider()
    memory_store = SqliteMemoryStore(factory, embeddings=embeddings)
    google_store = GoogleConnectionStore(factory, secret_key=settings.dashboard_secret_key)

    # -- security & tools ---------------------------------------------------
    auditlog = AuditLogImpl(factory)
    profiles_early = ProfileService(OwnerProfileRepositoryImpl(factory))
    onboarding = OnboardingService(profiles_early, audit=auditlog)
    memories = MemoryService(
        memory_store,
        audit=auditlog,
        secret=settings.dashboard_secret_key,
        onboarding=onboarding,
    )
    approvals_repo = ApprovalRepositoryImpl(factory)
    approval_gateway = ApprovalGatewayImpl(
        repo=approvals_repo,
        audit=auditlog,
        notifier=approval_notifier,
        durable=approval_notifier is None,
        ttl=ttl,
        clock=now,
    )
    policy = DEFAULT_POLICY

    registry = ToolRegistryImpl(
        policy=policy,
        approvals=approval_gateway,
        audit=auditlog,
    )
    registry.register_all([get_current_datetime])

    # -- model provider / agent ---------------------------------------------
    limits = {
        "max_tool_rounds": settings.run_max_tool_rounds,
        "max_seconds": settings.run_max_seconds,
    }
    if provider is not None:
        model_provider = provider
        agent: Agent | HermesAgent = Agent(provider=model_provider, registry=registry, **limits)
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
        agent = Agent(provider=fake, registry=registry, **limits)
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
            **limits,
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
            **limits,
        )
    profiles = profiles_early
    tasks = TaskService(task_repository, audit=auditlog, onboarding=onboarding)
    chat = ChatService(
        agent=agent,
        conversations=conversations,
        memory=memory_store,
        audit=auditlog,
        history_limit=settings.history_limit,
        runs=runs_repository,
        events=run_events,
        profiles=profiles,
        onboarding=onboarding,
        model_label=_model_label(settings),
        clock=now,
    )
    run_service = RunService(
        chat=chat, runs=runs_repository, broker=run_broker, approvals=approvals_repo
    )
    approval_service = ApprovalService(
        store=approvals_repo,
        registry=registry,
        audit=auditlog,
        resumer=run_service,
        ttl=ttl,
        clock=now,
        onboarding=onboarding,
    )
    registry.register_all(task_tools(tasks, profiles))
    registry.register_all(memory_tools(memories))

    google_token_provider = make_access_token_provider(store=google_store, settings=settings)
    google_client = GoogleApiClient(
        access_token_provider=google_token_provider,
        read_only_provider=google_store.is_read_only,
    )
    registry.register_all(google_tools(client=google_client, tasks=tasks))
    registry.register_all(web_tools())

    mcp_servers = McpServerStoreImpl(factory)
    mcp_adapter = McpToolAdapter()
    for server in mcp_servers.list():
        if server.enabled:
            registry.register_all(mcp_adapter.discover(server))

    telegram_allowed = build_allowed_chats(settings.telegram_allowed_chat_ids)
    telegram_client = (
        TelegramBotClient(settings.telegram_bot_token) if settings.telegram_bot_token else None
    )
    registry.register_all(
        telegram_tools(
            client=telegram_client,
            allowed_chat_ids=telegram_allowed,
            list_activity=lambda: list_telegram_audit_activity(auditlog, limit=50),
        )
    )
    telegram_worker = (
        TelegramWorker(
            TelegramBotRunner(
                client=telegram_client,
                chat_service=chat,
                audit=auditlog,
                allowed_chat_ids=telegram_allowed,
                approval_service=approval_service,
            )
        )
        if telegram_client
        else None
    )

    def _telegram_send(text: str) -> None:
        if telegram_client is None or not telegram_allowed:
            return
        chat_id = next(iter(telegram_allowed))
        telegram_client.send_message(chat_id, text)

    jobs = SqlJobQueue(factory)
    reminders = ReminderStoreImpl(factory)
    automations = AutomationStoreImpl(factory)
    scheduler = SchedulerService(
        jobs=jobs,
        reminders=reminders,
        automations=automations,
        tasks=tasks,
        profiles=profiles,
        approvals=approvals_repo,
        runs=runs_repository,
        audit=auditlog,
        telegram_send=_telegram_send if telegram_client else None,
        clock=now,
        owner_id="dashboard",
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
        runs=run_service,
        runs_repository=runs_repository,
        tasks=tasks,
        profiles=profiles,
        onboarding=onboarding,
        conversations=conversations,
        tasks_repository=task_repository,
        memory=memory_store,
        memories=memories,
        registry=registry,
        audit=auditlog,
        approvals=approval_gateway,
        approvals_repository=approvals_repo,
        approval_service=approval_service,
        google=google_store,
        scheduler=scheduler,
        reminders=reminders,
        automations=automations,
        mcp_servers=mcp_servers,
        mcp_adapter=mcp_adapter,
    )


def _model_label(settings: Settings) -> str:
    if settings.provider == "openai":
        return settings.openai_compat_model
    if settings.provider in ("ollama", "hermes"):
        return settings.ollama_model
    return "fake"


_app: AppContainer | None = None
_demo_app: AppContainer | None = None


def get_app(**build_kwargs) -> AppContainer:
    """Process-lifetime singleton app; tests pass build kwargs for fresh graphs."""
    global _app
    if _app is None or build_kwargs:
        _app = build_app(**build_kwargs)
    return _app


def reset_app() -> None:
    """Drop the cached container (mainly for test isolation)."""
    global _app, _demo_app
    _app = None
    _demo_app = None


def build_demo_settings(base: Settings | None = None) -> Settings:
    """Clone settings onto the isolated demo database with the fake provider."""
    from copy import copy

    settings = copy(base or load_settings())
    settings.provider = "fake"
    settings.database_url = settings.demo_database_url
    settings.telegram_bot_token = ""
    settings.google_client_id = ""
    settings.google_client_secret = ""
    return settings


def get_demo_app(*, settings: Settings | None = None, force_rebuild: bool = False) -> AppContainer:
    """Isolated demo workspace (UX-12). Never shares the owner DATABASE_URL."""
    global _demo_app
    from personal_agent.application.demo import ensure_demo_seeded, wrap_tools_as_simulated
    from personal_agent.domain.exceptions import ConfigurationError
    from personal_agent.infrastructure.model_providers.fake_provider import FakeProvider

    if _demo_app is not None and not force_rebuild and settings is None:
        return _demo_app

    owner = settings or load_settings()
    demo_settings = build_demo_settings(owner)
    if demo_settings.database_url == owner.database_url:
        raise ConfigurationError("Demo database must not equal the owner DATABASE_URL.")
    _demo_app = build_app(
        settings=demo_settings,
        provider=FakeProvider(
            default_content=(
                "This is the AURA demo. External actions are simulated and never leave "
                "this workspace. Try creating a task or asking for a draft email."
            )
        ),
    )
    wrap_tools_as_simulated(_demo_app.registry)
    ensure_demo_seeded(_demo_app)
    return _demo_app
