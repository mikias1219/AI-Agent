"""Runtime selection: Hermes only when local + installed + ≥64k context."""

import json

from personal_agent.config.settings import Settings
from personal_agent.infrastructure.model_providers.runtime_selection import (
    HERMES_MIN_CONTEXT_TOKENS,
    effective_hermes_base_url,
    is_local_inference_url,
    select_inference_runtime,
)


def _install_hermes(tmp_path):
    python = tmp_path / "python"
    python.write_text("")
    (tmp_path / "runtime.json").write_text(json.dumps({"python": str(python)}))
    return tmp_path


def test_fake_provider():
    choice = select_inference_runtime(Settings.from_env({"PERSONAL_AGENT_PROVIDER": "fake"}))
    assert choice.active_runtime == "fake"
    assert choice.use_hermes is False


def test_ollama_provider():
    choice = select_inference_runtime(Settings.from_env({"PERSONAL_AGENT_PROVIDER": "ollama"}))
    assert choice.active_runtime == "ollama_agent"
    assert choice.use_hermes is False


def test_openai_provider():
    choice = select_inference_runtime(
        Settings.from_env(
            {
                "PERSONAL_AGENT_PROVIDER": "openai",
                "OPENAI_COMPAT_API_KEY": "test-key",
            }
        )
    )
    assert choice.active_runtime == "openai_compat"
    assert choice.use_hermes is False
    assert "openai" in choice.reason.lower()


def test_hermes_falls_back_when_context_too_small(tmp_path):
    _install_hermes(tmp_path)
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "hermes",
            "HERMES_DIRECTORY": str(tmp_path),
            "HERMES_CONTEXT_TOKENS": "4096",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
        }
    )
    choice = select_inference_runtime(settings)
    assert choice.use_hermes is False
    assert choice.active_runtime == "ollama_agent"
    assert "64" in choice.reason or str(HERMES_MIN_CONTEXT_TOKENS) in choice.reason


def test_hermes_rejects_non_local_base_url(tmp_path):
    _install_hermes(tmp_path)
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "hermes",
            "HERMES_DIRECTORY": str(tmp_path),
            "HERMES_CONTEXT_TOKENS": str(HERMES_MIN_CONTEXT_TOKENS),
            "HERMES_BASE_URL": "https://openrouter.ai/api/v1",
        }
    )
    choice = select_inference_runtime(settings)
    assert choice.use_hermes is False
    assert "local" in choice.reason.lower() or "Non-local" in choice.reason


def test_hermes_selected_when_compatible(tmp_path):
    _install_hermes(tmp_path)
    settings = Settings.from_env(
        {
            "PERSONAL_AGENT_PROVIDER": "hermes",
            "HERMES_DIRECTORY": str(tmp_path),
            "HERMES_CONTEXT_TOKENS": str(HERMES_MIN_CONTEXT_TOKENS),
            "OLLAMA_BASE_URL": "http://localhost:11434",
        }
    )
    choice = select_inference_runtime(settings)
    assert choice.use_hermes is True
    assert choice.active_runtime == "hermes"
    assert choice.reason == ""
    assert is_local_inference_url(effective_hermes_base_url(settings))
