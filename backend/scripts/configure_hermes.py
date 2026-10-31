"""Securely configure and verify Hermes cloud inference before activating it."""

import getpass
import os
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "src"))

from personal_agent.app.container import build_app  # noqa: E402
from personal_agent.config.settings import load_settings  # noqa: E402


def save_environment(values):
    path = BACKEND / ".env"
    contents = path.read_text() if path.exists() else ""
    lines = [line for line in contents.splitlines() if line.partition("=")[0].strip() not in values]
    lines.extend(f"{key}={value}" for key, value in values.items())
    with tempfile.NamedTemporaryFile(mode="w", dir=BACKEND, prefix=".env.", delete=False) as stream:
        stream.write("\n".join(lines) + "\n")
        temporary = Path(stream.name)
    temporary.chmod(0o600)
    temporary.replace(path)


def main():
    os.chdir(BACKEND)
    settings = load_settings()
    key = settings.hermes_api_key or os.environ.get("OPENROUTER_API_KEY", "")
    if not key:
        if not sys.stdin.isatty():
            raise SystemExit(
                "Run this command in your terminal to enter your OpenRouter key privately."
            )
        key = getpass.getpass("OpenRouter API key (hidden): ").strip()
    if not key or any(character.isspace() for character in key):
        raise SystemExit("A valid API key is required. Configuration was not changed.")
    settings.hermes_model = settings.hermes_model or "qwen/qwen3.5-35b-a3b"
    settings.hermes_base_url = settings.hermes_base_url or "https://openrouter.ai/api/v1"
    settings.hermes_context_tokens = max(64000, settings.hermes_context_tokens)
    settings.hermes_api_key = key
    settings.hermes_directory = str(BACKEND / "data/hermes")
    settings.provider = "hermes"
    settings.telegram_bot_token = ""
    print("Testing Hermes with a short cloud request. No Telegram message will be sent.")
    with tempfile.TemporaryDirectory(prefix="hermes-verify-") as directory:
        settings.database_url = "sqlite:///" + str(Path(directory) / "check.db")
        container = build_app(settings=settings)
        try:
            _, reply = container.chat.turn(
                user_id="hermes-configuration-check", text="Reply briefly: Hermes is ready."
            )
        except Exception as exc:
            raise SystemExit(
                f"Verification failed ({type(exc).__name__}). The active provider was not changed."
            ) from None
        if not reply.strip():
            raise SystemExit("Hermes returned no reply. The active provider was not changed.")
    save_environment(
        {
            "HERMES_MODEL": settings.hermes_model,
            "HERMES_BASE_URL": settings.hermes_base_url,
            "HERMES_API_KEY": key,
            "HERMES_CONTEXT_TOKENS": str(settings.hermes_context_tokens),
            "HERMES_DIRECTORY": "data/hermes",
            "PERSONAL_AGENT_PROVIDER": "hermes",
        }
    )
    print(
        "Hermes verified and activated. Restart the dashboard, then start Telegram from its page."
    )


if __name__ == "__main__":
    main()
