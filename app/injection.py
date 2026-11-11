"""Deterministic screen for prompt-injection attempts, run before any model call.

The bot's first step is a model call that reads the visitor's message and the
chat history. That call costs money, and a message built to talk the model out
of its instructions should never reach it. This module answers one question with
rules alone: does this text look like an attempt to change the assistant's
instructions, read them out, or take over its role?

It is deliberately narrow. A medical site gets real questions that share words
with an attack ("ignore my earlier question", "what are your rules for
booking"), and refusing those is worse than missing a clever attack. Each
pattern therefore needs the attack's whole shape, not a single keyword, and the
control sentences in tests/test_injection.py are there to stop it drifting wide.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Words that can sit between "ignore" and "previous instructions" without
# changing the meaning: "ignore all of the above instructions".
_OVERRIDE_VERB = r"(?:ignore|disregard|forget|override|bypass)"
_OVERRIDE_FILLER = r"(?:\s+(?:all|any|the|your|my|of|these|those|its|previous|prior|above|earlier|old))*"
_OVERRIDE_TAIL = r"\s+(?:previous|prior|above|earlier)?\s*(?:instructions?|rules?|prompt|context|directives?|guidelines?)"

# A system prompt or instruction set is only exfiltration when the visitor asks
# to see it. "Can you show me the videos?" is a normal question and must pass.
_EXFIL_VERB = r"(?:print|reveal|show|repeat|output|display|tell\s+me|give\s+me|share|write\s+out|leak)"
_EXFIL_OBJECT = (
    r"(?:your|the|system|hidden|initial|original|internal)\s+"
    r"(?:system\s+prompt|prompt|instructions?|rules|configuration|guidelines)"
)

_CATEGORIES: list[tuple[str, re.Pattern[str]]] = [
    (
        "instruction_override",
        re.compile(_OVERRIDE_VERB + _OVERRIDE_FILLER + _OVERRIDE_TAIL, re.IGNORECASE),
    ),
    (
        "prompt_exfiltration",
        # "print your system prompt", "repeat the instructions you were given",
        # and the bare "word for word" request to reproduce something.
        re.compile(
            r"\b" + _EXFIL_VERB + r"\b[^.?!]{0,40}?\b" + _EXFIL_OBJECT + r"\b"
            r"|\bword\s+for\s+word\b",
            re.IGNORECASE,
        ),
    ),
    (
        "role_hijack",
        re.compile(
            r"\byou\s+are\s+now\b"
            r"|\bact\s+as\b"
            r"|\bpretend\s+to\s+be\b"
            r"|\bdeveloper\s+mode\b"
            r"|\bDAN\b"
            r"|\bjailbreak",
            re.IGNORECASE,
        ),
    ),
    (
        "delimiter_injection",
        re.compile(
            r"</?system>"
            r"|#{2,}\s*system"
            r"|<\|im_start\|>"
            r"|<\|system\|>",
            re.IGNORECASE,
        ),
    ),
]


@dataclass
class ScreenResult:
    blocked: bool
    category: str | None
    matched: str | None


def screen(text: str) -> ScreenResult:
    """Return the first category that matches, in the order above.

    The matched text is kept for the log, never for the reply: echoing a
    pattern back tells an attacker which rule fired and how to avoid it.
    """
    if not text:
        return ScreenResult(blocked=False, category=None, matched=None)
    for category, pattern in _CATEGORIES:
        match = pattern.search(text)
        if match:
            return ScreenResult(blocked=True, category=category, matched=match.group(0))
    return ScreenResult(blocked=False, category=None, matched=None)
