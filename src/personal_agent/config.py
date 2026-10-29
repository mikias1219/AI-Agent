"""Environment-driven settings for every entry point.

Precedence: real process environment overrides `.env` file values, which override
typed defaults. Secrets stay out of the repo and out of logs.
"""

from __future__ import annotations

import os
from pathlib import Path

from personal_agent.core.errors import ConfigurationError

ENV_FILE = Path(".env")

PROVIDERS = ("fake", "ollama")


class Settings:
    """Config as clear attributes; validated once at startup, never per call."""

    provider: str = "fake"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1:8b"
    database_url: str = "sqlite:///./data/agent.db"
    history_limit: int = 20
    approval_timeout_seconds: float = 10.0
    log_level: str = "INFO"

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

        try:
            settings.history_limit = max(1, int(env.get("HISTORY_LIMIT", settings.history_limit)))
            settings.approval_timeout_seconds = float(
                env.get("APPROVAL_TIMEOUT_SECONDS", settings.approval_timeout_seconds)
            )
        except ValueError as exc:
            raise ConfigurationError(f"Invalid numeric env value: {exc}") from exc

        settings.log_level = env.get("LOG_LEVEL", settings.log_level).upper()
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
    "DATABASE_URL",
    "HISTORY_LIMIT",
    "APPROVAL_TIMEOUT_SECONDS",
    "LOG_LEVEL",
)


def load_settings() -> Settings:
    """Standard entry point: `.env` overlaid by the process environment."""
    file_env = load_env_vars(ENV_FILE)
    process_env = {key: value for key in ASSEMBLY_KEYS if (value := os.environ.get(key))}
    return Settings.from_env({**file_env, **process_env})


def settings_defaults_demo() -> Settings:
    """Show defaults to tests/docs/tooling without reading files."""
    return Settings()
