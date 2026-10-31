"""Exercise the real process bridge without model downloads or external messages."""

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from personal_agent.config.settings import Settings
from personal_agent.domain.exceptions import ProviderError
from personal_agent.domain.models import Message, ToolContext, ToolSpec
from personal_agent.infrastructure.model_providers.hermes_agent import HermesAgent


@pytest.fixture
def bridge(tmp_path, monkeypatch):
    root = tmp_path / "hermes"
    root.mkdir()
    (root / "runtime.json").write_text(json.dumps({"python": sys.executable}))
    worker = tmp_path / "worker.py"
    worker.write_text("""
import json, os, sys
request = json.loads(sys.stdin.readline())
assert 'TELEGRAM_BOT_TOKEN' not in os.environ
assert 'DASHBOARD_SECRET_KEY' not in os.environ
assert request['model'] == 'llama3.1:8b'
print(json.dumps({'type':'tool','name':'task_list','id':'one','arguments':{}}), flush=True)
response = json.loads(sys.stdin.readline())
assert response == {'result':'owned tasks'}
print(json.dumps({'type':'delta','text':'Hello'}), flush=True)
print(json.dumps({'type':'done','text':'Hello owner'}), flush=True)
""")
    original = subprocess.Popen
    homes = []

    def start(command, **kwargs):
        homes.append(kwargs["env"]["HERMES_HOME"])
        return original([command[0], str(worker)], **kwargs)

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "must-not-leak")
    monkeypatch.setenv("DASHBOARD_SECRET_KEY", "must-not-leak")
    settings = Settings()
    settings.hermes_context_tokens = 64000
    settings.hermes_directory = str(root)
    calls = []

    class Registry:
        def specs(self):
            return [ToolSpec("task_list", "List tasks", {"type": "object"}, "read", None)]

        def execute(self, call, ctx):
            calls.append((call, ctx))
            return SimpleNamespace(ok=True, output="owned tasks")

    return HermesAgent(settings=settings, registry=Registry()), calls, homes, worker


def test_bridge_streams_and_preserves_tool_identity(bridge):
    agent, calls, homes, _ = bridge
    tokens = []
    ctx = ToolContext("dashboard", "session", "web")
    result = agent.run_turn([Message("user", "List my tasks")], ctx, on_token=tokens.append)
    assert result.final_text == "Hello owner"
    assert tokens == ["Hello"]
    assert calls[0][1] is ctx
    assert len(result.tool_calls_made) == 1
    assert Path(homes[0]).is_dir()


def test_bridge_memory_profiles_are_isolated(bridge):
    agent, _, homes, _ = bridge
    for user in ("dashboard", "telegram:group:other", "dashboard"):
        agent.run_turn([Message("user", "List my tasks")], ToolContext(user, "s", "telegram"))
    assert homes[0] == homes[2]
    assert homes[0] != homes[1]


def test_bridge_hides_upstream_errors(bridge):
    agent, _, _, worker = bridge
    worker.write_text(
        'import json; print(json.dumps({"type":"error","error_type":"RuntimeError"}))'
    )
    with pytest.raises(ProviderError, match="RuntimeError"):
        agent.run_turn([Message("user", "Hi")], ToolContext("a", "s", "web"))


def test_missing_install_is_actionable(tmp_path):
    settings = Settings()
    settings.hermes_context_tokens = 64000
    settings.hermes_directory = str(tmp_path)
    with pytest.raises(ProviderError, match="docs/hermes.md"):
        HermesAgent(settings=settings, registry=None).run_turn([], None)


def test_small_context_returns_actionable_error():
    with pytest.raises(ProviderError, match="64,000"):
        HermesAgent(settings=Settings(), registry=None).run_turn([], None)
