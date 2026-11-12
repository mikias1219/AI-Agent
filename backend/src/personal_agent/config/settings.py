"""Environment-driven settings for every entry point.

Precedence: real process environment overrides `.env` file values, which override
typed defaults. Secrets stay out of the repo and out of logs.
"""

from __future__ import annotations

import os
from pathlib import Path

from personal_agent.domain.exceptions import ConfigurationError

ENV_FILE = Path(".env")

PROVIDERS = ("fake", "ollama", "hermes", "openai")


class Settings:
    """Config as clear attributes; validated once at startup, never per call."""

    provider: str = "fake"
    hermes_directory: str = "data/hermes"
    hermes_model: str = ""
    hermes_base_url: str = ""
    hermes_api_key: str = ""
    hermes_context_tokens: int = 4096
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = 180.0
    ollama_context_tokens: int = 4096
    ollama_max_output_tokens: int = 256
    ollama_keep_alive: str = "10m"
    # OpenAI-compatible cloud inference (Groq / OpenRouter free models / etc.)
    openai_compat_base_url: str = "https://api.groq.com/openai/v1"
    openai_compat_api_key: str = ""
    openai_compat_model: str = "llama-3.1-8b-instant"
    openai_compat_timeout_seconds: float = 90.0
    openai_compat_max_output_tokens: int = 1024
    database_url: str = "sqlite:///./data/agent.db"
    history_limit: int = 20
    approval_ttl_seconds: float = 86400.0  # APR-05: 24 hours
    run_max_tool_rounds: int = 6  # BR-09
    run_max_seconds: float = 90.0  # BR-09
    log_level: str = "INFO"

    # Telegram integration (token is a secret: never log it)
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""  # comma/space list, e.g. "12345,-98765"
    dashboard_password_hash: str = ""
    dashboard_secret_key: str = ""
    # AUT-01: GitHub Actions tick; falls back to dashboard_secret_key when empty.
    internal_tick_secret: str = ""
    # local = loopback-only dashboard; production = Vercel↔Render cross-origin
    environment: str = "local"
    frontend_origin: str = ""  # e.g. https://your-app.vercel.app
    # Free Google Cloud OAuth client (user-owned). Empty = Google connect disabled.
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://127.0.0.1:8000/api/google/callback"
    # OBS-02: none | console (OTLP can be added later without changing callers)
    trace_exporter: str = "none"
    # UX-12: isolated demo database (never the owner DATABASE_URL)
    demo_database_url: str = "sqlite:///./data/demo.db"
    demo_rate_limit_per_minute: int = 60

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Settings:
        """Build Settings from a merged env mapping, validating as we go."""
        settings = cls()

        settings.provider = env.get("PERSONAL_AGENT_PROVIDER", settings.provider)
        if settings.provider not in PROVIDERS:
            raise ConfigurationError(
                f"Unknown provider {settings.provider!r}; choose one of {list(PROVIDERS)}."
            )

        raw_environment = env.get("ENVIRONMENT", settings.environment)
        settings.environment = raw_environment.strip().lower() or "local"
        if settings.environment not in ("local", "production"):
            raise ConfigurationError("ENVIRONMENT must be 'local' or 'production'.")
        raw_origin = env.get("FRONTEND_ORIGIN", settings.frontend_origin)
        settings.frontend_origin = raw_origin.strip().rstrip("/")
        if settings.environment == "production" and not settings.frontend_origin:
            raise ConfigurationError(
                "FRONTEND_ORIGIN is required when ENVIRONMENT=production "
                "(e.g. https://your-app.vercel.app)."
            )

        settings.hermes_directory = env.get("HERMES_DIRECTORY", settings.hermes_directory)
        settings.hermes_model = env.get("HERMES_MODEL", "").strip()
        settings.hermes_base_url = env.get("HERMES_BASE_URL", "").strip()
        settings.hermes_api_key = env.get("HERMES_API_KEY", "").strip()
        settings.ollama_base_url = env.get("OLLAMA_BASE_URL", settings.ollama_base_url)
        settings.ollama_model = env.get("OLLAMA_MODEL", settings.ollama_model)
        # Prefer explicit OPENAI_COMPAT_*; fall back to HERMES_* cloud keys already in secrets.
        settings.openai_compat_base_url = (
            env.get("OPENAI_COMPAT_BASE_URL", "").strip()
            or settings.hermes_base_url
            or settings.openai_compat_base_url
        )
        settings.openai_compat_api_key = (
            env.get("OPENAI_COMPAT_API_KEY", "").strip() or settings.hermes_api_key
        )
        settings.openai_compat_model = (
            env.get("OPENAI_COMPAT_MODEL", "").strip()
            or settings.hermes_model
            or settings.openai_compat_model
        )
        # Render blueprint historically forced provider=fake; if a free cloud key is
        # present in production, prefer real openai-compatible inference.
        if (
            settings.environment == "production"
            and settings.provider == "fake"
            and settings.openai_compat_api_key
        ):
            settings.provider = "openai"
        settings.database_url = normalize_database_url(
            env.get("DATABASE_URL", settings.database_url)
        )
        settings.ollama_keep_alive = env.get("OLLAMA_KEEP_ALIVE", settings.ollama_keep_alive)

        try:
            settings.hermes_context_tokens = int(env.get("HERMES_CONTEXT_TOKENS", 4096))
            if settings.hermes_context_tokens < 2048:
                raise ValueError("HERMES_CONTEXT_TOKENS must be at least 2048.")
            settings.ollama_timeout_seconds = float(
                env.get("OLLAMA_TIMEOUT_SECONDS", settings.ollama_timeout_seconds)
            )
            if settings.ollama_timeout_seconds <= 0:
                raise ValueError("OLLAMA_TIMEOUT_SECONDS must be greater than zero.")
            settings.ollama_context_tokens = int(
                env.get("OLLAMA_CONTEXT_TOKENS", settings.ollama_context_tokens)
            )
            settings.ollama_max_output_tokens = int(
                env.get("OLLAMA_MAX_OUTPUT_TOKENS", settings.ollama_max_output_tokens)
            )
            if settings.ollama_context_tokens < 2048 or settings.ollama_max_output_tokens < 64:
                raise ValueError("Use at least 2048 context tokens and 64 output tokens.")
            settings.openai_compat_timeout_seconds = float(
                env.get(
                    "OPENAI_COMPAT_TIMEOUT_SECONDS",
                    settings.openai_compat_timeout_seconds,
                )
            )
            if settings.openai_compat_timeout_seconds <= 0:
                raise ValueError("OPENAI_COMPAT_TIMEOUT_SECONDS must be greater than zero.")
            settings.openai_compat_max_output_tokens = int(
                env.get(
                    "OPENAI_COMPAT_MAX_OUTPUT_TOKENS",
                    settings.openai_compat_max_output_tokens,
                )
            )
            if settings.openai_compat_max_output_tokens < 64:
                raise ValueError("OPENAI_COMPAT_MAX_OUTPUT_TOKENS must be at least 64.")
            settings.history_limit = max(1, int(env.get("HISTORY_LIMIT", settings.history_limit)))
            settings.approval_ttl_seconds = float(
                env.get("APPROVAL_TTL_SECONDS", settings.approval_ttl_seconds)
            )
            settings.run_max_tool_rounds = max(
                1, int(env.get("RUN_MAX_TOOL_ROUNDS", settings.run_max_tool_rounds))
            )
            settings.run_max_seconds = max(
                1.0, float(env.get("RUN_MAX_SECONDS", settings.run_max_seconds))
            )
        except ValueError as exc:
            raise ConfigurationError(f"Invalid numeric env value: {exc}") from exc

        if settings.provider == "openai" and not settings.openai_compat_api_key:
            raise ConfigurationError(
                "PERSONAL_AGENT_PROVIDER=openai requires OPENAI_COMPAT_API_KEY "
                "(or HERMES_API_KEY) for the free cloud inference endpoint."
            )

        settings.log_level = env.get("LOG_LEVEL", settings.log_level).upper()

        settings.telegram_bot_token = env.get(
            "TELEGRAM_BOT_TOKEN", settings.telegram_bot_token
        ).strip()
        settings.telegram_allowed_chat_ids = env.get(
            "TELEGRAM_ALLOWED_CHAT_IDS", settings.telegram_allowed_chat_ids
        ).replace(" ", ",")
        settings.dashboard_password_hash = env.get(
            "DASHBOARD_PASSWORD_HASH", settings.dashboard_password_hash
        ).strip()
        settings.dashboard_secret_key = env.get(
            "DASHBOARD_SECRET_KEY", settings.dashboard_secret_key
        ).strip()
        settings.internal_tick_secret = env.get(
            "INTERNAL_TICK_SECRET", settings.internal_tick_secret
        ).strip()
        settings.google_client_id = env.get("GOOGLE_CLIENT_ID", settings.google_client_id).strip()
        settings.google_client_secret = env.get(
            "GOOGLE_CLIENT_SECRET", settings.google_client_secret
        ).strip()
        settings.google_redirect_uri = env.get(
            "GOOGLE_REDIRECT_URI", settings.google_redirect_uri
        ).strip()
        settings.trace_exporter = (
            env.get("TRACE_EXPORTER", settings.trace_exporter).strip().lower() or "none"
        )
        if settings.trace_exporter not in ("none", "console"):
            raise ConfigurationError("TRACE_EXPORTER must be 'none' or 'console'.")
        settings.demo_database_url = normalize_database_url(
            env.get("DEMO_DATABASE_URL", settings.demo_database_url)
        )
        try:
            settings.demo_rate_limit_per_minute = int(
                env.get("DEMO_RATE_LIMIT_PER_MINUTE", settings.demo_rate_limit_per_minute)
            )
        except ValueError as exc:
            raise ConfigurationError(f"Invalid DEMO_RATE_LIMIT_PER_MINUTE: {exc}") from exc
        if settings.demo_database_url == settings.database_url:
            raise ConfigurationError(
                "DEMO_DATABASE_URL must differ from DATABASE_URL so demo data never mixes."
            )
        return settings


def load_env_vars(path: Path) -> dict[str, str]:
    """Read a small `.env`-style file: KEY=VALUE lines, '#' comments, no interpolation."""
    if not path.is_file():
        return {}
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def normalize_database_url(database_url: str) -> str:
    """Prefer the psycopg3 driver for Postgres URLs from Supabase and similar hosts."""
    url = database_url.strip()
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url[len("postgres://") :]
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url[len("postgresql://") :]
    return url


ASSEMBLY_KEYS = (
    "PERSONAL_AGENT_PROVIDER",
    "HERMES_DIRECTORY",
    "HERMES_MODEL",
    "HERMES_BASE_URL",
    "HERMES_API_KEY",
    "HERMES_CONTEXT_TOKENS",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "OLLAMA_CONTEXT_TOKENS",
    "OLLAMA_MAX_OUTPUT_TOKENS",
    "OLLAMA_KEEP_ALIVE",
    "OPENAI_COMPAT_BASE_URL",
    "OPENAI_COMPAT_API_KEY",
    "OPENAI_COMPAT_MODEL",
    "OPENAI_COMPAT_TIMEOUT_SECONDS",
    "OPENAI_COMPAT_MAX_OUTPUT_TOKENS",
    "DATABASE_URL",
    "HISTORY_LIMIT",
    "APPROVAL_TTL_SECONDS",
    "LOG_LEVEL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_CHAT_IDS",
    "DASHBOARD_PASSWORD_HASH",
    "DASHBOARD_SECRET_KEY",
    "ENVIRONMENT",
    "FRONTEND_ORIGIN",
    "GOOGLE_CLIENT_ID",
    "GOOGLE_CLIENT_SECRET",
    "GOOGLE_REDIRECT_URI",
    "TRACE_EXPORTER",
    "INTERNAL_TICK_SECRET",
    "DEMO_DATABASE_URL",
    "DEMO_RATE_LIMIT_PER_MINUTE",
)


def load_settings() -> Settings:
    """Standard entry point: `.env` overlaid by the process environment."""
    file_env = load_env_vars(ENV_FILE)
    process_env = {key: value for key in ASSEMBLY_KEYS if (value := os.environ.get(key))}
    return Settings.from_env({**file_env, **process_env})


def update_dashboard_password_hash(password: str) -> None:
    """Replace the env-managed dashboard password hash without exposing the password."""
    import tempfile

    from personal_agent.application.security.passwords import hash_password

    if len(password) < 8:
        raise ConfigurationError("Use a password with at least 8 characters.")
    contents = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    lines = [
        line
        for line in contents.splitlines()
        if line.partition("=")[0].strip() != "DASHBOARD_PASSWORD_HASH"
    ]
    lines.append("DASHBOARD_PASSWORD_HASH=" + hash_password(password))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=ENV_FILE.parent, prefix=".env.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write("\n".join(lines) + "\n")
        temporary.chmod(0o600)
        temporary.replace(ENV_FILE)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()


def settings_defaults_demo() -> Settings:
    """Show defaults to tests/docs/tooling without reading files."""
    return Settings()


def initialize_dashboard_secret() -> bool:
    """Persist a signing key once, preserving other local environment settings."""
    import secrets
    import tempfile

    current = load_settings().dashboard_secret_key
    if current:
        if len(current) < 32:
            raise ConfigurationError("Replace the short DASHBOARD_SECRET_KEY in backend/.env.")
        return False
    contents = ENV_FILE.read_text(encoding="utf-8") if ENV_FILE.exists() else ""
    # Replace an empty assignment rather than introducing duplicate keys.
    lines = [
        line
        for line in contents.splitlines()
        if not line.strip().startswith("DASHBOARD_SECRET_KEY=")
    ]
    lines.append("DASHBOARD_SECRET_KEY=" + secrets.token_urlsafe(48))
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=ENV_FILE.parent, prefix=".env.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write("\n".join(lines) + "\n")
        temporary.chmod(0o600)
        temporary.replace(ENV_FILE)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return True
