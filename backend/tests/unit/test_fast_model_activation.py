"""The background setup must preserve secrets and reject an unverified model."""

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest


@pytest.mark.parametrize("outcome", ["success", "bad-tool", "new-choice"])
def test_activation_changes_model_only_after_validation(tmp_path, monkeypatch, outcome):
    spec = importlib.util.spec_from_file_location(
        "activate_fast_model",
        Path(__file__).resolve().parents[2] / "scripts" / "activate_fast_model.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.chdir(tmp_path)
    Path(".env").write_text("OLLAMA_MODEL=llama3.1:8b\nTELEGRAM_BOT_TOKEN=123:test-only\n")
    client = httpx.Client
    monkeypatch.setattr(
        module.httpx,
        "Client",
        lambda **kwargs: client(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"models": [{"name": module.MODEL}]})
            )
        ),
    )

    def build(settings):
        assert settings.telegram_bot_token == ""
        if outcome == "new-choice":
            Path(".env").write_text(
                "OLLAMA_MODEL=another-model\nTELEGRAM_BOT_TOKEN=123:test-only\n"
            )
        tasks = [] if outcome == "bad-tool" else [SimpleNamespace(title="Speed check")]
        return SimpleNamespace(
            tasks=SimpleNamespace(list=lambda: tasks),
            chat=SimpleNamespace(turn=lambda **kwargs: ("session", "Task created.")),
        )

    monkeypatch.setattr(module, "build_app", build)
    module.main()
    import json

    status = json.loads(Path("data/fast-model-setup.json").read_text())
    content = Path(".env").read_text()
    assert "TELEGRAM_BOT_TOKEN=123:test-only" in content
    if outcome == "success":
        assert "OLLAMA_MODEL=llama3.2:3b" in content
        assert status["restart_required"] is True
    elif outcome == "bad-tool":
        assert "OLLAMA_MODEL=llama3.1:8b" in content
        assert status["status"] == "validation_failed"
    else:
        assert "OLLAMA_MODEL=another-model" in content
        assert status["status"] == "model_selection_changed"


def test_public_setup_status_never_exposes_private_fields(tmp_path):
    from personal_agent.infrastructure.model_providers.setup_status import ModelSetupStatus

    path = tmp_path / "status.json"
    path.write_text('{"status":"waiting_for_download","model":"test-model","secret":"hidden"}')
    assert ModelSetupStatus(path).read() == {
        "status": "waiting_for_download",
        "model": "test-model",
    }
    path.write_text("invalid json")
    assert ModelSetupStatus(path).read() is None
