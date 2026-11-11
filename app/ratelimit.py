"""In-process rate limiting for the endpoints that spend money.

Each chat message costs one model call, and the lead form writes a row. A single
visitor repeating either costs real money, so both are limited per IP.

The limit is per key over a sliding window: a request is allowed while fewer
than `limit` timestamps sit in the last `window_seconds`. The process is single
instance behind the tunnel, so an in-memory deque is enough; a restarted process
forgets its counters, which is acceptable for a spend guard. Memory is bounded
because a key with no timestamp inside the window is deleted.
"""

from __future__ import annotations

import threading
import time
from collections import deque

from .config import settings


class RateLimiter:
    def __init__(self, limit: int, window_seconds: int, clock=time.monotonic) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str) -> tuple[bool, int]:
        """Record one attempt and say whether it may proceed.

        Returns (allowed, retry_after_seconds). retry_after is 0 when allowed,
        and otherwise the whole seconds until the oldest hit leaves the window.
        """
        with self._lock:
            now = self._clock()
            window_start = now - self.window_seconds

            # The same sweep that prunes this key also drops every other key
            # whose last hit has expired, so the dict cannot grow with traffic.
            for existing_key in list(self._hits):
                hits = self._hits[existing_key]
                while hits and hits[0] <= window_start:
                    hits.popleft()
                if not hits:
                    del self._hits[existing_key]

            hits = self._hits.setdefault(key, deque())

            if len(hits) >= self.limit:
                # hits[0] is the oldest one still counted; the wait ends when
                # it falls out of the window.
                remaining = hits[0] + self.window_seconds - now
                return False, max(1, int(remaining) + 1)

            hits.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter(
    limit=settings.rate_limit_requests,
    window_seconds=settings.rate_limit_window,
)
