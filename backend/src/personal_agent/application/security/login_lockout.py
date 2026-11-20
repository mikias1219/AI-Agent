"""Persisted login failure counters (S11). Survives process restart."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Any


class LoginLockoutStore:
    """File-backed IP lockout: after `max_failures`, lock for `lock_seconds`."""

    def __init__(
        self,
        path: Path,
        *,
        max_failures: int = 5,
        lock_seconds: float = 60.0,
    ) -> None:
        self._path = path
        self._max_failures = max(1, max_failures)
        self._lock_seconds = max(1.0, lock_seconds)
        self._mutex = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def is_locked(self, key: str) -> bool:
        with self._mutex:
            data = self._load()
            row = data.get(key) or {}
            locked_until = float(row.get("locked_until", 0.0))
            return time.time() < locked_until

    def record_failure(self, key: str) -> None:
        with self._mutex:
            data = self._load()
            row = dict(data.get(key) or {})
            failures = int(row.get("failures", 0)) + 1
            locked_until = 0.0
            if failures >= self._max_failures:
                locked_until = time.time() + self._lock_seconds
                failures = 0
            data[key] = {"failures": failures, "locked_until": locked_until}
            self._save(data)

    def clear(self, key: str) -> None:
        with self._mutex:
            data = self._load()
            if key in data:
                del data[key]
                self._save(data)

    def _load(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {}
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return raw if isinstance(raw, dict) else {}

    def _save(self, data: dict[str, Any]) -> None:
        # Drop expired locks to keep the file small.
        now = time.time()
        pruned = {
            key: row
            for key, row in data.items()
            if isinstance(row, dict)
            and (int(row.get("failures", 0)) > 0 or float(row.get("locked_until", 0.0)) > now)
        }
        tmp = self._path.with_suffix(".tmp")
        tmp.write_text(json.dumps(pruned, indent=0), encoding="utf-8")
        tmp.replace(self._path)


def csv_safe_cell(value: object) -> str:
    """Neutralise spreadsheet formula injection (S10)."""
    text = "" if value is None else str(value)
    if text and text[0] in {"=", "+", "-", "@", "\t", "\r"}:
        return "'" + text
    return text


__all__ = ["LoginLockoutStore", "csv_safe_cell"]
