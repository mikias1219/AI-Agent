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
