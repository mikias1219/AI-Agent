"""Executed only with Hermes's Python, not imported by the web application."""

import contextlib
import json
import os
import sys
import tempfile
import traceback
import uuid
from pathlib import Path


def main():
    protocol_out = sys.stdout
    request = json.loads(sys.stdin.readline())
    sys.path.insert(0, sys.argv[1])
    home = Path(os.environ["HERMES_HOME"])
    config = {
        "model": {
            "default": request["model"],
            "provider": "custom",
            "base_url": request["base_url"],
            "context_length": request["context_tokens"],
        },
        "compression": {"enabled": False},
        "auxiliary": {"title_generation": {"enabled": False}},
        "telemetry": {"shared_metrics": {"enabled": False, "send": False}},
    }
    with tempfile.NamedTemporaryFile(mode="w", dir=home, delete=False) as stream:
        json.dump(config, stream)
        temporary = Path(stream.name)
    temporary.replace(home / "config.yaml")

    def emit(event):
        protocol_out.write(json.dumps(event) + "\n")
        protocol_out.flush()

    # Upstream startup/tool diagnostics must never corrupt our JSON protocol.
    with contextlib.redirect_stdout(sys.stderr):
        import hermes_bootstrap  # noqa: F401
        from run_agent import AIAgent
        from tools.registry import registry

        def handler(name):
            def invoke(args, **kwargs):
                emit({"type": "tool", "id": str(uuid.uuid4()), "name": name, "arguments": args})
                return sys.stdin.readline().strip()

            return invoke

        for tool in request["tools"]:
            registry.register(
                name=tool["name"],
                toolset="workspace",
                schema=tool,
                handler=handler(tool["name"]),
            )
        history = request["history"]
        system = "\n\n".join(m["content"] for m in history if m["role"] == "system")
        messages = [m for m in history if m["role"] != "system"]
        agent = AIAgent(
            model=request["model"],
            provider="custom",
            api_key=request["api_key"],
            base_url=request["base_url"],
            enabled_toolsets=["workspace", "memory", "skills"],
            max_iterations=5,
            max_tokens=request["max_tokens"],
            run_budget_seconds=request["timeout"],
            quiet_mode=True,
            skip_context_files=True,
            skip_background_review=True,
            stream_delta_callback=lambda text: (
                emit({"type": "delta", "text": text}) if text else None
            ),
        )
        try:
            result = agent.run_conversation(
                messages[-1]["content"],
                system_message=system,
                conversation_history=messages[:-1],
            )
            if result.get("error") or result.get("completed") is False:
                raise RuntimeError("Incomplete Hermes turn")
            text = result.get("final_response", "").strip()
            if not text:
                raise RuntimeError("Empty Hermes turn")
            emit({"type": "done", "text": text})
        finally:
            agent.close()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        traceback.print_exc(file=sys.stderr)
        # Never send upstream exception bodies (which can contain credentials) to clients.
        sys.stdout.write(json.dumps({"type": "error", "error_type": type(exc).__name__}) + "\n")
        sys.stdout.flush()
        sys.exit(1)
