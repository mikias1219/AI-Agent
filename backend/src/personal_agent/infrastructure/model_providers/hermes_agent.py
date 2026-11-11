"""Hermes orchestration in an isolated process; workspace tools stay behind our gate."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path

from personal_agent.application.run_events import emit_event
from personal_agent.application.tools.selection import select_tools
from personal_agent.domain.exceptions import AgentError, ProviderError
from personal_agent.domain.models import CancellationToken, Message, RunOutcome, ToolCall


class HermesAgent:
    def __init__(self, *, settings, registry):
        self.settings = settings
        self.registry = registry

    def run_turn(self, history, ctx, on_token=None, cancel: CancellationToken | None = None):
        if self.settings.hermes_context_tokens < 64000:
            raise ProviderError(
                "Hermes requires at least 64,000 context tokens. Configure a compatible model "
                "in backend/.env using docs/hermes.md; the current local model uses 4,096."
            )
        root = Path(self.settings.hermes_directory).resolve()
        try:
            python = Path(json.loads((root / "runtime.json").read_text())["python"])
        except (OSError, ValueError, KeyError) as exc:
            raise ProviderError("Hermes is not installed. Follow docs/hermes.md.") from exc
        if not python.is_file():
            raise ProviderError("Hermes is not installed. Follow docs/hermes.md.")
        identity = hashlib.sha256(ctx.user_id.encode()).hexdigest()[:24]
        home = root / "home" / "profiles" / identity
        home.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Do not pass dashboard credentials, Telegram tokens or cloud keys to Hermes.
        env = {
            k: os.environ[k] for k in ("PATH", "HOME", "LANG", "SSL_CERT_FILE") if k in os.environ
        }
        env.update(
            HOME=str(home),
            HERMES_HOME=str(home),
            PYTHONUNBUFFERED="1",
            HERMES_TELEMETRY_ENABLED="false",
        )
        worker = Path(__file__).with_name("hermes_worker.py")
        process = subprocess.Popen(
            [str(python), str(worker), str(root / "source")],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            env=env,
            cwd=home,
        )
        events = queue.Queue()

        def read_events():
            for line in process.stdout:
                events.put(line)
            events.put(None)

        threading.Thread(target=read_events, daemon=True).start()
        tools = select_tools(history, self.registry.specs())
        payload = {
            "history": [
                {"role": m.role, "content": m.content}
                for m in history
                if m.role in ("system", "user", "assistant") and not m.tool_calls
            ],
            "tools": [
                {
                    "name": t.name,
                    "description": t.description,
                    "parameters": dict(t.parameters_schema),
                }
                for t in tools
            ],
            "model": (self.settings.hermes_model or self.settings.ollama_model),
            "base_url": (
                self.settings.hermes_base_url or self.settings.ollama_base_url.rstrip("/") + "/v1"
            ),
            "context_tokens": self.settings.hermes_context_tokens,
            "api_key": self.settings.hermes_api_key or "ollama",
            "max_tokens": self.settings.ollama_max_output_tokens,
            "timeout": self.settings.ollama_timeout_seconds,
        }
        outcome = RunOutcome(final_text="")
        deadline = time.monotonic() + self.settings.ollama_timeout_seconds

        def send(data):
            process.stdin.write(json.dumps(data) + "\n")
            process.stdin.flush()

        try:
            send(payload)
            while True:
                if cancel is not None and cancel.cancelled:
                    outcome.stop_reason = "cancelled"
                    outcome.final_text = "I stopped because you asked me to."
                    outcome.new_messages.append(
                        Message(role="assistant", content=outcome.final_text)
                    )
                    return outcome
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise ProviderError("Hermes timed out. Check the local model and retry.")
                try:
                    line = events.get(timeout=min(remaining, 0.5))
                except queue.Empty:
                    continue
                if line is None:
                    raise ProviderError("Hermes stopped unexpectedly. Check its installation.")
                event = json.loads(line)
                if event["type"] == "delta":
                    emit_event(ctx, "token", text=event["text"])
                    if on_token:
                        on_token(event["text"])
                elif event["type"] == "tool":
                    call = ToolCall(
                        id=event["id"], name=event["name"], arguments=event["arguments"]
                    )
                    # Defense in depth: only explicitly advertised workspace tools may run.
                    if call.name not in {t.name for t in tools}:
                        send({"error": "Tool unavailable"})
                        continue
                    emit_event(
                        ctx,
                        "tool.started",
                        call_id=call.id,
                        name=call.name,
                        arguments=dict(call.arguments),
                    )
                    started = time.monotonic()
                    try:
                        result = self.registry.execute(call, ctx)
                        send({"result": result.output} if result.ok else {"error": result.error})
                        ok, text = result.ok, result.output if result.ok else result.error
                    except AgentError as exc:
                        send({"error": str(exc)})
                        ok, text = False, str(exc)
                    emit_event(
                        ctx,
                        "tool.finished",
                        call_id=call.id,
                        name=call.name,
                        ok=ok,
                        output=text or "",
                        duration_ms=int((time.monotonic() - started) * 1000),
                    )
                    outcome.tool_calls_made.append(call)
                elif event["type"] == "done":
                    outcome.final_text = event["text"]
                    outcome.new_messages.append(Message(role="assistant", content=event["text"]))
                    return outcome
                elif event["type"] == "error":
                    raise ProviderError(
                        "Hermes could not finish the request (" + event["error_type"] + ")."
                    )
        except (OSError, ValueError, KeyError) as exc:
            raise ProviderError("Hermes communication failed. Check its installation.") from exc
        finally:
            if process.poll() is None:
                with contextlib.suppress(OSError):
                    # Sandbox or race: process may already be gone / not signalable.
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
            with contextlib.suppress(OSError):
                process.stdin.close()
            with contextlib.suppress(OSError):
                process.stdout.close()
