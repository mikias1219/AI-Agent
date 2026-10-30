"""Environment-driven settings for every entry point.

Precedence: real process environment overrides `.env` file values, which override
typed defaults. Secrets stay out of the repo and out of logs.
"""

from __future__ import annotations

import os
from pathlib import Path

from personal_agent.domain.exceptions import ConfigurationError

ENV_FILE = Path(".env")

PROVIDERS = ("fake", "ollama")


class Settings:
    """Config as clear attributes; validated once at startup, never per call."""

    provider: str = "fake"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout_seconds: float = 180.0
    ollama_context_tokens: int = 4096
    ollama_max_output_tokens: int = 256
    ollama_keep_alive: str = "10m"
    database_url: str = "sqlite:///./data/agent.db"
    history_limit: int = 20
    approval_timeout_seconds: float = 10.0
    log_level: str = "INFO"

    # Telegram integration (token is a secret: never log it)
    telegram_bot_token: str = ""
    telegram_allowed_chat_ids: str = ""  # comma/space list, e.g. "12345,-98765"
    dashboard_password_hash: str = ""
    dashboard_secret_key: str = ""

    @classmethod
    def from_env(cls, env: dict[str, str]) -> Settings:
        """Build Settings from a merged env mapping, validating as we go."""
        settings = cls()

        settings.provider = env.get("PERSONAL_AGENT_PROVIDER", settings.provider)
        if settings.provider not in PROVIDERS:
            raise ConfigurationError(
                f"Unknown provider {settings.provider!r}; choose one of {list(PROVIDERS)}."
            )

        settings.ollama_base_url = env.get("OLLAMA_BASE_URL", settings.ollama_base_url)
        settings.ollama_model = env.get("OLLAMA_MODEL", settings.ollama_model)
        settings.database_url = env.get("DATABASE_URL", settings.database_url)
        settings.ollama_keep_alive = env.get("OLLAMA_KEEP_ALIVE", settings.ollama_keep_alive)

        try:
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
            settings.history_limit = max(1, int(env.get("HISTORY_LIMIT", settings.history_limit)))
            settings.approval_timeout_seconds = float(
                env.get("APPROVAL_TIMEOUT_SECONDS", settings.approval_timeout_seconds)
            )
        except ValueError as exc:
            raise ConfigurationError(f"Invalid numeric env value: {exc}") from exc

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


ASSEMBLY_KEYS = (
    "PERSONAL_AGENT_PROVIDER",
    "OLLAMA_BASE_URL",
    "OLLAMA_MODEL",
    "OLLAMA_TIMEOUT_SECONDS",
    "OLLAMA_CONTEXT_TOKENS",
    "OLLAMA_MAX_OUTPUT_TOKENS",
    "OLLAMA_KEEP_ALIVE",
    "DATABASE_URL",
    "HISTORY_LIMIT",
    "APPROVAL_TIMEOUT_SECONDS",
    "LOG_LEVEL",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_ALLOWED_CHAT_IDS",
    "DASHBOARD_PASSWORD_HASH",
    "DASHBOARD_SECRET_KEY",
)


def load_settings() -> Settings:
    """Standard entry point: `.env` overlaid by the process environment."""
    file_env = load_env_vars(ENV_FILE)
    process_env = {key: value for key in ASSEMBLY_KEYS if (value := os.environ.get(key))}
    return Settings.from_env({**file_env, **process_env})


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
