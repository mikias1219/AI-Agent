"""Provider settings validation."""

from __future__ import annotations

import pytest

from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import ConfigurationError


def test_ollama_timeout_defaults_to_long_local_inference_window():
    settings = Settings.from_env({})

    assert settings.ollama_timeout_seconds == 180.0


@pytest.mark.parametrize("value", ["0", "-1", "not-a-number"])
def test_invalid_ollama_timeout_is_rejected(value):
    with pytest.raises(ConfigurationError):
        Settings.from_env({"OLLAMA_TIMEOUT_SECONDS": value})


def test_dashboard_initialization_preserves_settings_and_existing_key(tmp_path, monkeypatch):
    from pathlib import Path

    from personal_agent.config import settings as module

    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DASHBOARD_SECRET_KEY", raising=False)
    monkeypatch.setattr(module, "ENV_FILE", Path(".env"))
    Path(".env").write_text("TELEGRAM_BOT_TOKEN=123:test-only\nDASHBOARD_SECRET_KEY=\n")
    assert module.initialize_dashboard_secret() is True
    first = Path(".env").read_text()
    assert "TELEGRAM_BOT_TOKEN=123:test-only" in first
    assert len(module.load_settings().dashboard_secret_key) >= 32
    assert module.initialize_dashboard_secret() is False
    assert Path(".env").read_text() == first


@pytest.mark.parametrize(
    "key,value",
    [
        ("OLLAMA_CONTEXT_TOKENS", "100"),
        ("OLLAMA_MAX_OUTPUT_TOKENS", "1"),
        ("OLLAMA_MAX_OUTPUT_TOKENS", "not-a-number"),
    ],
)
def test_invalid_inference_budgets_are_rejected(key, value):
    with pytest.raises(ConfigurationError):
        Settings.from_env({key: value})


def test_production_requires_frontend_origin():
    with pytest.raises(ConfigurationError):
        Settings.from_env({"ENVIRONMENT": "production"})


def test_postgres_urls_prefer_psycopg_driver():
    settings = Settings.from_env(
        {
            "DATABASE_URL": "postgresql://user:pass@db.example:5432/postgres",
            "ENVIRONMENT": "production",
            "FRONTEND_ORIGIN": "https://app.example",
        }
    )
    assert settings.database_url.startswith("postgresql+psycopg://")
    assert settings.frontend_origin == "https://app.example"


def test_openai_falls_back_to_hermes_cloud_secrets():
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "openai",
            "HERMES_API_KEY": "gsk_test",
            "HERMES_BASE_URL": "https://api.groq.com/openai/v1",
            "HERMES_MODEL": "llama-3.1-8b-instant",
        }
    )
    assert settings.openai_compat_api_key == "gsk_test"
    assert settings.openai_compat_base_url == "https://api.groq.com/openai/v1"
    assert settings.openai_compat_model == "llama-3.1-8b-instant"


def test_openai_requires_api_key():
    with pytest.raises(ConfigurationError):
        Settings.from_env({"PERSONAL_AGENT_PROVIDER": "openai"})


def test_production_fake_upgrades_to_openai_when_key_present():
    settings = Settings.from_env(
        {
            "ENVIRONMENT": "production",
            "FRONTEND_ORIGIN": "https://app.example",
            "PERSONAL_AGENT_PROVIDER": "fake",
            "HERMES_API_KEY": "gsk_test",
        }
    )
    assert settings.provider == "openai"
    assert settings.openai_compat_api_key == "gsk_test"


def test_run_limits_default_to_br09_and_are_configurable() -> None:
    from personal_agent.config.settings import Settings

    defaults = Settings.from_env({"PERSONAL_AGENT_PROVIDER": "fake"})
    assert (defaults.run_max_tool_rounds, defaults.run_max_seconds) == (6, 90.0)
    custom = Settings.from_env(
        {"PERSONAL_AGENT_PROVIDER": "fake", "RUN_MAX_TOOL_ROUNDS": "3", "RUN_MAX_SECONDS": "30"}
    )
    assert (custom.run_max_tool_rounds, custom.run_max_seconds) == (3, 30.0)
