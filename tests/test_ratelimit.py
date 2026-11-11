"""Tests for the in-process rate limiter.

The clock is injected so the window can be moved forward without sleeping.
"""

from __future__ import annotations

from app.ratelimit import RateLimiter


class FakeClock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_allows_up_to_the_limit_then_blocks():
    clock = FakeClock()
    limiter = RateLimiter(limit=3, window_seconds=60, clock=clock)

    for _ in range(3):
        allowed, retry_after = limiter.allow("1.2.3.4")
        assert allowed
        assert retry_after == 0

    allowed, retry_after = limiter.allow("1.2.3.4")
    assert not allowed
    assert retry_after >= 1


def test_window_expiry_allows_again():
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window_seconds=60, clock=clock)

    assert limiter.allow("a")[0]
    assert limiter.allow("a")[0]
    assert not limiter.allow("a")[0]

    clock.advance(61)
    allowed, retry_after = limiter.allow("a")
    assert allowed
    assert retry_after == 0


def test_sliding_window_frees_one_slot_at_a_time():
    clock = FakeClock()
    limiter = RateLimiter(limit=2, window_seconds=60, clock=clock)

    assert limiter.allow("a")[0]
    clock.advance(30)
    assert limiter.allow("a")[0]
    assert not limiter.allow("a")[0]

    # The first hit leaves the window, the second is still inside it.
    clock.advance(31)
    assert limiter.allow("a")[0]
    assert not limiter.allow("a")[0]


def test_keys_are_independent():
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window_seconds=60, clock=clock)

    assert limiter.allow("a")[0]
    assert not limiter.allow("a")[0]
    assert limiter.allow("b")[0]


def test_expired_keys_are_pruned():
    clock = FakeClock()
    limiter = RateLimiter(limit=1, window_seconds=60, clock=clock)

    for key in ("a", "b", "c"):
        assert limiter.allow(key)[0]
    assert len(limiter._hits) == 3

    clock.advance(61)
    assert limiter.allow("d")[0]
    # a, b and c all expired inside the window, so only d remains.
    assert list(limiter._hits) == ["d"]
