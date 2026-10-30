"""Wait for the approved model download, validate tools, then update local settings.

Run from backend/. Does not start Telegram, send messages, or restart user processes.
Progress is written to data/fast-model-setup.json; the old model is retained.
"""

from __future__ import annotations

import copy
import json
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx

from personal_agent.app.container import build_app
from personal_agent.config.settings import load_env_vars, load_settings

MODEL = "llama3.2:3b"
STATUS = Path("data/fast-model-setup.json")


def report(state: str, **details) -> None:
    STATUS.parent.mkdir(parents=True, exist_ok=True)
    value = {
        "status": state,
        "model": MODEL,
        "updated_at": datetime.now(UTC).isoformat(),
        **details,
    }
    temporary = STATUS.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(STATUS)
    print(state, flush=True)


def main() -> None:
    settings = load_settings()
    original = load_env_vars(Path(".env")).get("OLLAMA_MODEL", settings.ollama_model)
    report("waiting_for_download", active_model=settings.ollama_model)
    deadline = time.monotonic() + 7200
    with httpx.Client(timeout=10) as http:
        while time.monotonic() < deadline:
            try:
                response = http.get(settings.ollama_base_url.rstrip("/") + "/api/tags")
                response.raise_for_status()
                if any(m.get("name") == MODEL for m in response.json().get("models", [])):
                    break
            except (httpx.HTTPError, ValueError):
                pass
            time.sleep(15)
        else:
            report("download_not_ready", active_model=original)
            return
    report("validating_tool_use", active_model=original)
    candidate = copy.copy(settings)
    candidate.provider = "ollama"
    candidate.ollama_model = MODEL
    candidate.ollama_timeout_seconds = 90
    candidate.telegram_bot_token = ""
    with tempfile.TemporaryDirectory(prefix="fast-model-check-") as directory:
        candidate.database_url = f"sqlite:///{Path(directory) / 'check.db'}"
        container = build_app(settings=candidate)
        started = time.monotonic()
        _, reply = container.chat.turn(
            user_id="speed-validation",
            text=("Create a task named Speed check. Then confirm its exact title."),
        )
        tasks = container.tasks.list()
        if len(tasks) != 1 or tasks[0].title.casefold() != "speed check" or not reply.strip():
            report(
                "validation_failed",
                active_model=original,
                reason="The smaller model did not correctly create the test task.",
            )
            return
        elapsed = round(time.monotonic() - started, 2)
    # Do not overwrite a different model choice made while the download was running.
    current = load_env_vars(Path(".env")).get("OLLAMA_MODEL", settings.ollama_model)
    if current not in {original, MODEL}:
        report("model_selection_changed", active_model=current)
        return
    updates = {
        "OLLAMA_MODEL": MODEL,
        "OLLAMA_MAX_OUTPUT_TOKENS": "256",
        "OLLAMA_CONTEXT_TOKENS": "4096",
        "OLLAMA_KEEP_ALIVE": "10m",
    }
    path = Path(".env")
    contents = path.read_text() if path.exists() else ""
    lines = [
        line for line in contents.splitlines() if line.partition("=")[0].strip() not in updates
    ]
    lines.extend(f"{key}={value}" for key, value in updates.items())
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", dir=".", prefix=".env.fast-model.", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write("\n".join(lines) + "\n")
        temporary.chmod(0o600)
        temporary.replace(path)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    report(
        "ready_restart_required",
        previous_model=original,
        tool_check_seconds=elapsed,
        restart_required=True,
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        report("activation_failed", error_type=type(exc).__name__)
        raise
