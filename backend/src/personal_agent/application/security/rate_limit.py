"""Simple sliding-window rate limiter for dashboard API endpoints (S8)."""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    """In-process per-key limit: at most `limit` events per `window_seconds`."""

    def __init__(self, *, limit: int, window_seconds: float = 60.0) -> None:
        self._limit = max(1, limit)
        self._window = max(1.0, window_seconds)
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self._window:
                bucket.popleft()
            if len(bucket) >= self._limit:
                return False
            bucket.append(now)
            return True


__all__ = ["SlidingWindowRateLimiter"]
