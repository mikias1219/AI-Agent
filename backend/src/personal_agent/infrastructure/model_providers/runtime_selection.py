"""Choose Hermes vs local Ollama agent loop without calling paid cloud inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from personal_agent.config.settings import Settings

HERMES_MIN_CONTEXT_TOKENS = 64000


@dataclass(frozen=True, slots=True)
class RuntimeChoice:
    """Resolved inference path for this process."""

    active_runtime: str  # hermes | ollama_agent | fake
    reason: str
    use_hermes: bool


def hermes_installed(hermes_directory: str) -> bool:
    root = Path(hermes_directory)
    if not root.is_absolute():
        root = Path.cwd() / root
    try:
        payload = (root / "runtime.json").read_text(encoding="utf-8")
    except OSError:
        return False
    try:
        import json

        python = Path(json.loads(payload)["python"])
    except (ValueError, KeyError, TypeError):
        return False
    return python.is_file()


def effective_hermes_base_url(settings: Settings) -> str:
    if settings.hermes_base_url.strip():
        return settings.hermes_base_url.strip().rstrip("/")
    return settings.ollama_base_url.rstrip("/") + "/v1"


def is_local_inference_url(url: str) -> bool:
    """True for localhost / 127.0.0.1 OpenAI-compatible or Ollama URLs."""
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower()
    return host in {"localhost", "127.0.0.1", "::1"}


def probe_ollama_reachable(base_url: str, timeout_seconds: float = 1.5) -> bool:
    """True when the local Ollama HTTP API answers (no model download)."""
    try:
        import httpx
    except ImportError:
        return False
    url = base_url.rstrip("/") + "/api/tags"
    try:
        with httpx.Client(timeout=timeout_seconds) as client:
            response = client.get(url)
        return response.status_code < 500
    except (httpx.HTTPError, OSError):
        return False


def select_inference_runtime(settings: Settings) -> RuntimeChoice:
    """Pick the execution path. Never selects paid cloud model endpoints."""
    if settings.provider == "fake":
        return RuntimeChoice(active_runtime="fake", reason="", use_hermes=False)

    if settings.provider == "ollama":
        return RuntimeChoice(
            active_runtime="ollama_agent",
            reason="PERSONAL_AGENT_PROVIDER=ollama",
            use_hermes=False,
        )

    # provider == hermes
    installed = hermes_installed(settings.hermes_directory)
    base_url = effective_hermes_base_url(settings)
    local = is_local_inference_url(base_url)

    if not installed:
        return RuntimeChoice(
            active_runtime="ollama_agent",
            reason="Hermes is not installed; using the local Ollama agent loop.",
            use_hermes=False,
        )
    if settings.hermes_context_tokens < HERMES_MIN_CONTEXT_TOKENS:
        return RuntimeChoice(
            active_runtime="ollama_agent",
            reason=(
                f"Hermes needs at least {HERMES_MIN_CONTEXT_TOKENS} context tokens; "
                f"configured {settings.hermes_context_tokens}. Using the local Ollama agent loop."
            ),
            use_hermes=False,
        )
    if not local:
        return RuntimeChoice(
            active_runtime="ollama_agent",
            reason=(
                "Non-local Hermes base URL is not supported (local Ollama only). "
                "Using the local Ollama agent loop."
            ),
            use_hermes=False,
        )
    return RuntimeChoice(active_runtime="hermes", reason="", use_hermes=True)
