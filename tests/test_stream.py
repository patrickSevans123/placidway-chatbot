"""Tests for the streaming hold-back filter.

The property under test is the one that matters: text may stream, but no money
amount reaches the browser unless it was in the evidence. Each test states the
failure it prevents, because the filter looks arbitrary until you see what it is
guarding.
"""

from __future__ import annotations

import random

from app.stream import MoneyHoldback, format_sse

EVIDENCE = (
    "The Out-Patient Program is 18,995 USD for three weeks. "
    "The In-Patient Program is 30,000 USD for the same three weeks."
)


def run(deltas: list[str], evidence: str = EVIDENCE) -> tuple[str, bool]:
    hold = MoneyHoldback(evidence)
    out = "".join(hold.feed(delta) for delta in deltas)
    tail, ok = hold.finish()
    return out + tail, ok


def test_supported_price_survives_any_split_unchanged():
    text = "It is $18,995 USD for three weeks."
    for cut in range(1, len(text)):
        emitted, ok = run([text[:cut], text[cut:]])
        assert emitted == text, f"split at {cut} produced {emitted!r}"
        assert ok


def test_unsupported_price_never_reaches_the_client():
    emitted, ok = run(["The package is $", "9,500", " USD today."])
    assert "9,500" not in emitted
    assert "9500" not in emitted
    assert ok is False


def test_bare_unsupported_price_is_also_dropped():
    # No dollar sign and no currency word: the shape a model uses when it
    # paraphrases, and the shape that used to escape the guard entirely.
    emitted, ok = run(["The package is 9,500 USD."])
    assert "9,500" not in emitted
    assert ok is False


def test_a_price_is_not_released_before_it_is_complete():
    hold = MoneyHoldback(EVIDENCE)
    assert hold.feed("The cost is $18") == "The cost is "
    assert hold.feed(",99") == ""
    assert hold.feed("5 USD") == "$18,995 USD"


def test_ordinary_numbers_are_never_dropped():
    # A trailing number may be held for one chunk, because "18995" could still
    # become "18995 USD". It must never be dropped, and must arrive intact.
    emitted, ok = run(["The program lasts 3", " weeks, 19 FAQs, 2026."])
    assert emitted == "The program lasts 3 weeks, 19 FAQs, 2026."
    assert ok


def test_a_short_number_streams_without_waiting():
    # "3" cannot become a price by gaining digits, so it is not held at all.
    hold = MoneyHoldback(EVIDENCE)
    assert hold.feed("The program lasts 3") == "The program lasts 3"


def test_a_word_ending_in_us_is_not_held():
    # A naive "ends with US" check would hold CAMPUS until the buffer cap.
    hold = MoneyHoldback(EVIDENCE)
    assert hold.feed("CAMPUS") == "CAMPUS"


def test_currency_suffix_form_is_checked():
    emitted, ok = run(["The package is 30,000", " USD."])
    assert "30,000" in emitted
    assert ok

    emitted, ok = run(["The package is 44,000", " USD."])
    assert "44,000" not in emitted
    assert ok is False


def test_us_dollar_prefix_form_is_checked():
    emitted, ok = run(["It is US", "$18,995", " total."])
    assert "18,995" in emitted
    assert ok


def test_a_dangling_dollar_holds_and_then_releases():
    hold = MoneyHoldback(EVIDENCE)
    assert hold.feed("Cost: $") == "Cost: "
    assert hold.feed("18,995") == ""
    assert hold.feed(" USD.") == "$18,995 USD."


def test_random_splits_never_leak_an_unsupported_amount():
    text = (
        "The Out-Patient Program is $18,995 USD [1]. "
        "A second opinion costs $2,400 USD, and the full programme is 9,500 USD [2]."
    )
    rng = random.Random(7)
    for _ in range(60):
        cuts = sorted(rng.sample(range(1, len(text)), 5))
        pieces = [text[i:j] for i, j in zip([0, *cuts], [*cuts, len(text)], strict=True)]
        emitted, ok = run(pieces)
        assert "9,500" not in emitted
        assert "2,400" not in emitted
        assert "18,995" in emitted
        assert ok is False


def test_format_sse_keeps_accents_literal():
    frame = format_sse("token", {"text": "El precio es 18.995 dólares"})
    assert "dólares" in frame
    assert "\\u" not in frame
    assert frame.startswith("event: token\ndata: ")
    assert frame.endswith("\n\n")


# -- the model client ----------------------------------------------------


class _StubSettings:
    llm_api_key = "test-key"
    llm_base_url = "https://example.invalid/v1"
    llm_model = "test-model"
    llm_temperature = 0.0
    llm_timeout = 5.0
    llm_fallbacks: tuple[str, ...] = ()


def test_chat_stream_reads_a_server_sent_event_body(monkeypatch):
    import httpx

    from app import llm

    monkeypatch.setattr(llm, "settings", _StubSettings())
    body = (
        'data: {"choices":[{"delta":{"content":"Hello "}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"world"}}]}\n\n'
        "data: [DONE]\n\n"
    )
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)))

    deltas = list(llm.chat_stream([{"role": "user", "content": "hi"}], client=client))

    assert "".join(delta.text for delta in deltas) == "Hello world"
    assert deltas[-1].model == "test-model"
    assert deltas[-1].latency_ms is not None


def test_chat_stream_accepts_a_plain_json_body(monkeypatch):
    # Some gateways answer a streaming request with one JSON body. That is a
    # complete answer, not an error.
    import httpx

    from app import llm

    monkeypatch.setattr(llm, "settings", _StubSettings())
    body = '{"choices":[{"message":{"content":"Hello world"}}]}'
    client = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, text=body)))

    deltas = list(llm.chat_stream([{"role": "user", "content": "hi"}], client=client))

    assert "".join(delta.text for delta in deltas) == "Hello world"
    assert deltas[-1].model == "test-model"
