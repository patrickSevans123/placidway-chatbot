"""Streaming primitives that cannot publish an invented price.

With token streaming the text leaves the server long before `guard.check` runs on
the finished answer. A naive implementation would show an invented figure for a
second and then retract it, which is worse than not streaming at all.

`MoneyHoldback` closes that gap with one rule: a span that could still become a
money mention is held back until it completes, and is then released only if its
value appears in the evidence that was supplied to the model. The rest of the
text is emitted immediately, so the stream still feels live.

The definition of a price is `guard.money_spans`, reused rather than
reimplemented: what the stream releases and what the final guard accepts have to
be the same definition, or the two would disagree about the same sentence.

This module is pure. No I/O, and nothing imported from `app.llm`.
"""

from __future__ import annotations

import json
import re

from .guard import money_spans

# A digit-and-separator run at the very end of the buffer. The number may still
# be growing, so it cannot be checked yet.
_TRAILING_RUN_RE = re.compile(r"\d[\d.,]*$")
# A currency opener with nothing after it yet. The word boundary matters: a plain
# search would hold "CAMPUS" forever because it ends in "US".
_OPEN_PREFIX_RE = re.compile(r"(?<![A-Za-z])(?:US\s*\$?|\$)\s*$")
# The same, used to pull a "$" into the held span so a dropped price takes its
# currency sign with it instead of leaving a bare "$" on screen.
_PREFIX_AT_END_RE = re.compile(r"(?<![A-Za-z])(?:US\s*\$|\$)\s*$")

# Past this, holding does more harm than good: emit and let the final guard
# correct the answer through the `replace` event.
_BUFFER_CAP = 64


def format_sse(event: str, data: dict) -> str:
    """Render one server-sent event.

    `ensure_ascii=False` keeps accented Spanish and Arabic literal in the frame
    instead of turning every non-ASCII character into a `\\u` escape.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


class MoneyHoldback:
    """Emit generated text while never releasing an unsupported money amount.

    Guarantee: for any sequence of `feed` calls,
    `"".join(emitted) + finish()[0]` contains no money amount absent from the
    evidence. An unsupported span is dropped, never replaced with a placeholder.
    """

    def __init__(self, evidence: str) -> None:
        self._allowed = {value for _, _, value in money_spans(evidence)}
        self._buf = ""
        self.ok = True

    def feed(self, delta: str) -> str:
        """Take a chunk of generated text, return the part that is safe to send."""
        self._buf += delta
        cut = self._open_tail(self._buf)
        closed, self._buf = self._buf[:cut], self._buf[cut:]
        out = self._scrub(closed)

        if len(self._buf) > _BUFFER_CAP:
            out += self._scrub(self._buf)
            self._buf = ""

        return out

    def finish(self) -> tuple[str, bool]:
        """Flush whatever is left, and report whether anything was suppressed."""
        rest, self._buf = self._buf, ""
        return self._scrub(rest), self.ok

    # -- internals --------------------------------------------------------

    def _open_tail(self, text: str) -> int:
        """Index where a still-growing money mention begins, or `len(text)`."""
        opener = _OPEN_PREFIX_RE.search(text)
        if opener:
            return opener.start()

        run = _TRAILING_RUN_RE.search(text)
        if run and self._could_be_money(text, run.start(), run.group()):
            opener = _PREFIX_AT_END_RE.search(text[: run.start()])
            return opener.start() if opener else run.start()

        return len(text)

    @staticmethod
    def _could_be_money(text: str, start: int, run: str) -> bool:
        before = text[:start]
        if _OPEN_PREFIX_RE.search(before):
            # "$18" and "US$18,99" are money from the first digit.
            return True
        # With no currency marker, a bare run is only a possible price when a
        # separator groups it, or it is long enough that " USD" may still come.
        # "3" in "3 weeks" therefore streams immediately.
        return "," in run or "." in run or len(run) >= 3

    def _scrub(self, text: str) -> str:
        """Keep every supported amount, drop every unsupported one."""
        spans = money_spans(text)
        if not spans:
            return text

        kept: list[str] = []
        last = 0
        for start, end, value in spans:
            kept.append(text[last:start])
            if value in self._allowed:
                kept.append(text[start:end])
            else:
                self.ok = False
            last = end
        kept.append(text[last:])
        return "".join(kept)


__all__ = ["MoneyHoldback", "format_sse"]
