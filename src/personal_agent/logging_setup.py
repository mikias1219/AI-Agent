"""Structured logging with convention names and light redaction.

Never log secrets. Credentials used by integrations will carry a `secret=True`
marker; the filter below ensures they never reach a handler.
"""

from __future__ import annotations

import contextlib
import logging
import re
from datetime import UTC, datetime

from personal_agent.config import Settings

SECRET_HINTS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*\S+"),
)


def redact(message: str) -> str:
    """Replace likely credential values with a mask (never logs the real value)."""
    redacted = message
    for pattern in SECRET_HINTS:
        redacted = pattern.sub(r"\1=***", redacted)
    return redacted


class RedactionFilter(logging.Filter):
    """Applies `redact` to every record's message text before emission."""

    def filter(self, record: logging.LogRecord) -> bool:
        with contextlib.suppress(Exception):  # logging must never crash the app
            record.msg = redact(record.getMessage())
            record.args = ()  # msg is now final text; clear %-style args
        return True


def configure_logging(settings: Settings) -> logging.RootLogger:
    """Install the app-wide logging setup; return the root logger for tests."""
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(settings.log_level)
    # Noisy third-party libraries below our own app logging threshold.
    for noisy in ("httpx", "httpcore", "urllib3", "alembic"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    root.debug(
        "Logging configured at %s (start=%s).",
        settings.log_level,
        datetime.now(UTC).isoformat(timespec="seconds"),
    )
    return root
