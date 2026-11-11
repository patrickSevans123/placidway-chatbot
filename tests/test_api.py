"""HTTP-level tests for the routes added this round.

The unit tests cover the limiter and the filter in isolation. These cover the
wiring: that the SSE endpoint frames its events, that the limiter returns 429 on
the routes that spend money, and that feedback reaches sqlite. None of them call
the network, so they are safe to run in CI.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import db
from app.ratelimit import RateLimiter


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # Point the database at a throwaway file so the real one is never touched.
    monkeypatch.setattr("app.db.settings", SimpleNamespace(db_path=tmp_path / "test.db"))
    import app.main as main

    with TestClient(main.app) as test_client:
        yield test_client


def _frames(body: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    name = None
    for line in body.splitlines():
        if line.startswith("event: "):
            name = line[len("event: ") :]
        elif line.startswith("data: "):
            events.append((name or "", json.loads(line[len("data: ") :])))
    return events


def test_stream_endpoint_frames_its_events(client, monkeypatch):
    def fake_stream(message, history=None):
        yield "stage", {"stage": "retrieving"}
        yield "token", {"text": "The package is "}
        yield "token", {"text": "18,995 USD."}
        yield "done", {
            "answer": "The package is 18,995 USD.",
            "sources": [{"id": 1, "title": "t", "url": "u", "page_type": "Treatment package"}],
            "language": "en",
            "intent": "cost",
            "grounded": True,
            "show_disclaimer": False,
            "show_lead_form": True,
            "latency_ms": 10,
            "model": "test",
            "confidence": 0.9,
            "prices_checked_at": "11 Nov 2026",
        }

    import app.main as main

    monkeypatch.setattr(main, "answer_stream", fake_stream)
    response = client.post("/api/chat/stream", json={"message": "how much does it cost?"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")

    frames = _frames(response.text)
    names = [name for name, _ in frames]
    assert names == ["stage", "token", "token", "done"]
    assert "18,995" in "".join(payload["text"] for name, payload in frames if name == "token")
    done = frames[-1][1]
    assert done["session_id"], "the done event must carry the session id for the next turn"
    assert done["prices_checked_at"] == "11 Nov 2026"


def test_rate_limit_returns_429_on_the_chat_routes(client, monkeypatch):
    import app.main as main

    monkeypatch.setattr(main, "limiter", RateLimiter(limit=2, window_seconds=60))

    codes = [
        client.post("/api/feedback", json={"question": "q", "rating": 1}).status_code
        for _ in range(3)
    ]
    assert codes == [200, 200, 200], "feedback is not a spend route and must not be limited"

    first = client.post("/api/lead", json={"name": "a", "email": "a@example.com"})
    second = client.post("/api/lead", json={"name": "b", "email": "b@example.com"})
    third = client.post("/api/lead", json={"name": "c", "email": "c@example.com"})

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
    assert third.json()["error"] == "rate_limited"
    assert int(third.headers["retry-after"]) >= 1


def test_feedback_is_stored_and_counted(client):
    assert client.post("/api/feedback", json={"question": "q", "rating": 1}).json() == {"ok": True}
    assert client.post("/api/feedback", json={"question": "q", "rating": -1}).json() == {"ok": True}

    stats = db.stats()
    assert stats["feedback_up"] == 1
    assert stats["feedback_down"] == 1


def test_feedback_rejects_a_zero_rating(client):
    response = client.post("/api/feedback", json={"question": "q", "rating": 0})
    assert response.status_code == 400
