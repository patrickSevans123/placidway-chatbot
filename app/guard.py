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
MONEY_RE = re.compile(r"(?:US\s*\$|\$)\s?(\d{1,3}(?:,\d{3})+|\d+(?:\.\d{1,2})?)")
MONEY_SUFFIX_RE = re.compile(r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d{1,2})?)\s?(?:USD|usd|dollars?)")

# Sentences that assert the information is not available. Deliberately narrow:
# "not included" is excluded because it is a normal phrase in a package
# description ("flights are not included"), not a refusal.
ABSENCE_RE = re.compile(
    r"\b(?:not\s+(?:listed|available|mentioned|stated|specified|provided|documented)|"
    r"no\s+(?:price|information|details|data|mention)|"
    r"(?:don'?t|do not|doesn'?t|does not)\s+(?:have|mention|say|specify|state|list|provide)|"
    r"(?:cannot|can'?t|unable to)\s+find|"
    r"not\s+in\s+(?:the|our)\s+(?:content|knowledge|pages|sources))\b",
    re.IGNORECASE,
)


@dataclass
class GuardResult:
    ok: bool
    issues: list[str] = field(default_factory=list)
    cited: list[int] = field(default_factory=list)
    unsupported_amounts: list[float] = field(default_factory=list)


def amounts_in(text: str) -> list[float]:
    values: list[float] = []
    for match in MONEY_RE.finditer(text):
        values.append(float(match.group(1).replace(",", "")))
    for match in MONEY_SUFFIX_RE.finditer(text):
        values.append(float(match.group(1).replace(",", "")))
    return values


def cited_ids(answer: str) -> list[int]:
    return sorted({int(m.group(1)) for m in CITATION_RE.finditer(answer)})


def check(
    answer: str,
    *,
    evidence: str,
    source_count: int,
    require_citation: bool = True,
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

    if ABSENCE_RE.search(answer) and answer_amounts:
        issues.append("answer claims the information is missing but still states a price")

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
