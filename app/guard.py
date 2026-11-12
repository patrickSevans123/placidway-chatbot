"""Deterministic checks that run on every generated answer.

Prompting alone does not stop a model from inventing a price. These checks are
cheap, rule-based and run after generation, before the answer reaches the user:

  * citation check   - every `[n]` must point at a source that was actually
                       supplied, and an answer with no citation is rejected;
  * numeric check    - every money amount in the answer must appear in the
                       evidence that was supplied, compared after normalising
                       "$18,995", "18995" and "18,995 USD" to the same value;
  * refusal check    - an answer that claims the corpus has no information must
                       not also contain a price.

When a check fails the caller regenerates once with a stricter instruction. If
it fails again the answer is replaced with the honest fallback, so a wrong price
can never reach the user.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CITATION_RE = re.compile(r"\[(\d{1,2})\]")
# Three ways a price is written in these pages, and all three have to be caught,
# or a model can state a figure the guard never looks at:
#   $18,995 / US$18,995       currency prefix
#   18,995 USD / 18.995 USD   currency suffix
#   18,995                    bare, thousands separator only
# The third form is how a model paraphrases a price ("the package is 18,995"),
# and until now it slipped through every check. It is deliberately narrow: a
# separator is required, so "3 weeks", "19 FAQs" and "2026" are never amounts.
MONEY_RE = re.compile(r"(?:US\s*\$|\$)\s?(\d[\d.,]*)")
MONEY_SUFFIX_RE = re.compile(r"(\d[\d.,]*)\s?(?:USD|usd|dollars?|d[oó]lares?)")
MONEY_BARE_RE = re.compile(
    r"(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{1,3}(?:\.\d{3})+)(?!\d)"
)
MONEY_PATTERNS = (MONEY_RE, MONEY_SUFFIX_RE, MONEY_BARE_RE)


def _to_float(raw: str) -> float | None:
    """Parse a number written with either thousands convention.

    "18,995" and "18.995" are both eighteen thousand nine hundred ninety-five.
    "18.99" is eighteen point nine nine. The rule: a separator followed by
    exactly three digits is a thousands separator; anything else is a decimal.
    """
    raw = raw.strip().rstrip(".,")
    if not raw:
        return None

    if "," in raw and "." in raw:
        if raw.rfind(",") > raw.rfind("."):
            raw = raw.replace(".", "").replace(",", ".")
        else:
            raw = raw.replace(",", "")
    elif "," in raw:
        parts = raw.split(",")
        raw = raw.replace(",", "") if len(parts[-1]) == 3 else raw.replace(",", ".")
    elif "." in raw:
        parts = raw.split(".")
        if len(parts[-1]) == 3:
            raw = raw.replace(".", "")

    try:
        return float(raw)
    except ValueError:
        return None

# Sentences that assert the information is not available. Deliberately narrow:
# "not included" is excluded because it is a normal phrase in a package
# description ("flights are not included"), not a refusal.
ABSENCE_RE = re.compile(
    r"\b(?:not\s+(?:listed|available|mentioned|stated|specified|provided|documented|covered)|"
    r"no\s+(?:price|information|details|data|mention)|"
    r"(?:don'?t|do not|doesn'?t|does not)\s+(?:have|mention|say|specify|state|list|provide|cover)|"
    r"(?:say|says|said|state|states)\s+nothing|nothing\s+(?:about|on|in)\b|"
    r"(?:cannot|can'?t|unable to)\s+find|"
    r"(?:isn'?t|is not|aren'?t|are not)\s+on\s+(?:the|these|our)\s+pages|"
    r"not\s+in\s+(?:the|our)\s+(?:content|knowledge|pages|sources))\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)
    unsupported_amounts: list[float] = field(default_factory=list)


def money_spans(text: str) -> list[tuple[int, int, float]]:
    """Every money mention as `(start, end, value)`, left to right, no overlaps.

    Spans rather than values, because the streaming filter has to remove exactly
    the characters of an unsupported price and keep the text around it. The
    longest match wins: in "18,995 USD" the suffix form beats the bare "18,995"
    inside it, so the currency word is removed with the number.
    """
    found: list[tuple[int, int, float]] = []
    for pattern in MONEY_PATTERNS:
        for match in pattern.finditer(text):
            value = _to_float(match.group(1))
            if value is not None:
                found.append((match.start(), match.end(), value))

    found.sort(key=lambda span: (span[0], -span[1]))
    spans: list[tuple[int, int, float]] = []
    for span in found:
        if spans and span[0] < spans[-1][1]:
            continue
        spans.append(span)
    return spans


def amounts_in(text: str) -> list[float]:
    return [value for _, _, value in money_spans(text)]


def cited_ids(answer: str) -> list[int]:
    return sorted({int(m.group(1)) for m in CITATION_RE.finditer(answer)})


def check(
    answer: str,
    *,
    evidence: str,
    source_count: int,
    require_citation: bool = True,
    blocks: dict[int, str] | None = None,
) -> GuardResult:
    issues: list[str] = []
    cited = cited_ids(answer)

    if require_citation and not cited:
        issues.append("no citation marker in answer")

    phantom = [c for c in cited if c < 1 or c > source_count]
    if phantom:
        issues.append(f"cites sources that were not supplied: {phantom}")

    evidence_amounts = set(amounts_in(evidence))
    answer_amounts = amounts_in(answer)
    unsupported = [a for a in answer_amounts if a not in evidence_amounts]
    if unsupported:
        issues.append(f"money amounts not present in evidence: {sorted(set(unsupported))}")

    # Only a contradiction when the absence and the price sit in the same
    # sentence. "The inpatient price is not listed, but the outpatient program
    # is 18,995" is a partial answer, not a contradiction.
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        if ABSENCE_RE.search(sentence) and amounts_in(sentence):
            issues.append("answer claims the information is missing but still states a price")
            break

    # A citation that points at a page which does not contain the figure is a
    # grounding failure even when the number itself is real. The visitor clicks
    # the link, finds no such price, and stops trusting the answer.
    if blocks:
        for sentence in re.split(r"(?<=[.!?])\s+", answer):
            amounts = amounts_in(sentence)
            if not amounts:
                continue
            cited_here = [int(m.group(1)) for m in CITATION_RE.finditer(sentence)]
            if not cited_here:
                continue
            cited_amounts: set[float] = set()
            for cid in cited_here:
                cited_amounts.update(amounts_in(blocks.get(cid, "")))
            missing = [a for a in amounts if a not in cited_amounts]
            if missing:
                issues.append(
                    f"cited source does not contain the price {sorted(set(missing))} in: {sentence[:70]!r}"
                )
                break

    return GuardResult(
        ok=not issues,
        issues=issues,
        cited=cited,
        unsupported_amounts=sorted(set(unsupported)),
    )


def strip_unsupported_sentences(answer: str, evidence: str) -> str:
    """Remove sentences that contain a money amount absent from the evidence.

    Used as a last resort before falling back to a refusal: it keeps the parts
    of the answer that are supported instead of discarding all of it.
    """
    evidence_amounts = set(amounts_in(evidence))
    kept: list[str] = []
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        bad = [a for a in amounts_in(sentence) if a not in evidence_amounts]
        if bad:
            continue
        kept.append(sentence)
    return " ".join(kept).strip()
