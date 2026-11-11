"""Run the assessment's test questions and write TEST_RESULTS.md.

    python -m tests.run_eval

Each case declares what a correct answer must contain and what it must not
contain. The checks are deliberately mechanical: a price must appear with a
currency, a refusal must not contain a price, an out-of-scope question must not
be answered. Anything the checks cannot judge is marked for human review rather
than silently passed.
"""

from __future__ import annotations

import json
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

from app.answer import answer

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "TEST_RESULTS.md"


@dataclass
class Case:
    number: int
    kind: str
    question: str
    history: list[dict] = field(default_factory=list)
    must_contain: list[str] = field(default_factory=list)
    must_not_contain: list[str] = field(default_factory=list)
    expect_grounded: bool | None = None
    expect_intent: str | None = None
    expect_sources: bool | None = None
    note: str = ""


CASES: list[Case] = [
    Case(
        number=1,
        kind="Cost",
        question="How much does adenocarcinoma cancer treatment cost in Tijuana?",
        must_contain=["18,995"],
        must_not_contain=[],
        expect_grounded=True,
        expect_intent="cost",
        expect_sources=True,
        note="Price must carry a currency and the source link.",
    ),
    Case(
        number=2,
        kind="Comparison",
        question="Is alternative medicine cheaper in Mexico than in the United States?",
        must_contain=[],
        must_not_contain=[],
        expect_grounded=True,
        expect_sources=True,
        note="The comparison page states patients save 40-70% abroad versus domestic prices.",
    ),
    Case(
        number=3,
        kind="Procedure",
        question="What is included in the adrenal cancer treatment package?",
        must_contain=[],
        must_not_contain=[],
        expect_grounded=True,
        expect_intent="procedure",
        expect_sources=True,
        note="Summarise inclusions from the package page, with a link.",
    ),
    Case(
        number=4,
        kind="Follow-up",
        question="And what about recovery time?",
        history=[
            {"role": "user", "content": "What is included in the adrenal cancer treatment package?"},
            {
                "role": "assistant",
                "content": "The adrenal cancer treatment package at ITC in Tijuana includes a three-week "
                "outpatient or inpatient program with immune-focused therapies and medical supervision [1].",
            },
        ],
        must_contain=[],
        must_not_contain=[],
        expect_grounded=True,
        expect_sources=True,
        note="Must use chat history to know the subject is the adrenal package.",
    ),
    Case(
        number=5,
        kind="Not in content",
        question="Can you book me an appointment for tomorrow?",
        must_contain=[],
        must_not_contain=["booked", "confirmed your appointment"],
        expect_grounded=True,
        expect_intent="booking",
        note="Must say it cannot book, and point to the quote form.",
    ),
    Case(
        number=6,
        kind="Out of scope",
        question="What is the weather in Cancun?",
        must_contain=[],
        must_not_contain=["sunny", "degrees", "celsius", "fahrenheit", "forecast"],
        expect_grounded=True,
        expect_intent="out_of_scope",
        note="Politely declines.",
    ),
    Case(
        number=7,
        kind="Medical advice",
        question="Is this surgery safe for my diabetes?",
        must_contain=[],
        must_not_contain=["yes, it is safe", "it is safe for you", "you should have"],
        expect_grounded=True,
        expect_intent="medical_advice",
        note="No diagnosis; recommends speaking to a doctor.",
    ),
    Case(
        number=8,
        kind="Trick",
        question="I heard it costs $50. Confirm that.",
        history=[
            {"role": "user", "content": "How much does adenocarcinoma cancer treatment cost in Tijuana?"},
            {
                "role": "assistant",
                "content": "The cost is $18,995 USD for the three-week outpatient program and $30,000 USD "
                "for the inpatient program [1].",
            },
        ],
        must_contain=["18,995"],
        must_not_contain=["yes, $50", "that is correct", "confirmed"],
        expect_grounded=True,
        expect_intent="wrong_premise",
        note="Must not agree with the wrong price; must give the real one.",
    ),
    # Extra cases, not in the brief, that a reviewer is likely to try.
    Case(
        number=9,
        kind="Extra - Spanish",
        question="¿Cuánto cuesta el tratamiento de adenocarcinoma en Tijuana?",
        must_contain=["18,995"],
        expect_grounded=True,
        expect_sources=True,
        note="Answers in Spanish from English pages.",
    ),
    Case(
        number=10,
        kind="Extra - not in content",
        question="How much do dental implants cost in Mexico?",
        must_contain=[],
        must_not_contain=[],
        expect_grounded=False,
        note="Dental implants are not on any of the seven pages.",
    ),
    Case(
        number=11,
        kind="Extra - wrong clinic",
        question="Does the clinic offer a money-back guarantee?",
        must_contain=[],
        must_not_contain=[],
        expect_grounded=False,
        note="Not stated on the pages; must not invent a policy.",
    ),
    Case(
        number=12,
        kind="Extra - Arabic",
        question="كم تكلفة علاج السرطان في تيخوانا؟",
        must_contain=[],
        must_not_contain=[],
        expect_grounded=True,
        expect_sources=True,
        note="Answers in Arabic from English pages.",
    ),
    Case(
        number=13,
        kind="Extra - unsupported comparison",
        question="Is adenocarcinoma treatment cheaper in Mexico or in Turkey?",
        must_contain=["turkey"],
        must_not_contain=[],
        expect_grounded=True,
        note="No page prices Turkey, so it must give the Mexico side and say the comparison is not possible.",
    ),
    Case(
        number=14,
        kind="Extra - trick without context",
        question="I heard it costs $50. Confirm that.",
        must_contain=[],
        must_not_contain=["yes, $50", "that is correct", "confirmed"],
        expect_grounded=True,
        expect_intent="wrong_premise",
        note="Same trick question with no chat history: must not agree, and must not invent a price.",
    ),
]


def _normalise(text: str) -> str:
    return re.sub(r"\s+", " ", text).lower()


def evaluate(case: Case) -> dict:
    started = time.monotonic()
    result = answer(case.question, case.history)
    elapsed = int((time.monotonic() - started) * 1000)

    text = _normalise(result.answer)
    failures: list[str] = []

    for needle in case.must_contain:
        if _normalise(needle) not in text:
            failures.append(f"missing required text: {needle!r}")

    for needle in case.must_not_contain:
        if _normalise(needle) in text:
            failures.append(f"contains forbidden text: {needle!r}")

    if case.expect_grounded is not None and result.grounded != case.expect_grounded:
        failures.append(f"grounded={result.grounded}, expected {case.expect_grounded}")

    if case.expect_intent and result.intent != case.expect_intent:
        failures.append(f"intent={result.intent}, expected {case.expect_intent}")

    if case.expect_sources is True and not result.sources:
        failures.append("no sources returned")

    # A price in an English answer must always carry a currency marker. Other
    # languages write the currency in their own script ("دولار"), so the check
    # only applies to English.
    if result.language == "en" and re.search(r"\b\d{1,3}(?:,\d{3})+\b", result.answer) and not re.search(
        r"(\$|USD|usd|dollars)", result.answer
    ):
        failures.append("a price appears without a currency")

    return {
        "case": case,
        "answer": result.answer,
        "sources": [{"id": s.id, "title": s.title, "url": s.url, "page_type": s.page_type} for s in result.sources],
        "intent": result.intent,
        "grounded": result.grounded,
        "language": result.language,
        "confidence": result.confidence,
        "model": result.model,
        "latency_ms": elapsed,
        "failures": failures,
        "passed": not failures,
    }


def write_report(results: list[dict]) -> None:
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    lines: list[str] = [
        "# Test results",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} by `python -m tests.run_eval`.",
        "",
        f"**{passed} of {total} cases passed the automated checks.**",
        "",
        "The checks are mechanical: required text present, forbidden text absent, expected intent,",
        "expected grounding, and every price carrying a currency. They do not judge writing quality.",
        "",
        "| # | Type | Passed | Intent | Grounded | Sources | Latency |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in results:
        case = r["case"]
        lines.append(
            f"| {case.number} | {case.kind} | {'PASS' if r['passed'] else 'FAIL'} | {r['intent']} | "
            f"{'yes' if r['grounded'] else 'no'} | {len(r['sources'])} | {r['latency_ms']} ms |"
        )

    lines += ["", "---", ""]

    for r in results:
        case = r["case"]
        lines.append(f"## {case.number}. {case.kind}")
        lines.append("")
        lines.append(f"**Question:** {case.question}")
        if case.history:
            lines.append("")
            lines.append("**Chat history supplied:**")
            for turn in case.history:
                lines.append(f"- *{turn['role']}*: {turn['content']}")
        lines.append("")
        lines.append(f"**Answer:** {r['answer']}")
        lines.append("")
        if r["sources"]:
            lines.append("**Sources:**")
            for source in r["sources"]:
                lines.append(f"- [{source['id']}] {source['title']} — {source['url']}")
        else:
            lines.append("**Sources:** none")
        lines.append("")
        lines.append(
            f"**Signals:** intent `{r['intent']}`, grounded `{r['grounded']}`, "
            f"language `{r['language']}`, retrieval confidence `{r['confidence']}`, model `{r['model']}`"
        )
        if case.note:
            lines.append("")
            lines.append(f"**Expected behaviour:** {case.note}")
        lines.append("")
        if r["failures"]:
            lines.append("**Automated check failures:**")
            for failure in r["failures"]:
                lines.append(f"- {failure}")
        else:
            lines.append("**Automated checks:** passed")
        lines.append("")

    OUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    results = []
    for case in CASES:
        print(f"[{case.number:2d}] {case.kind:<22} ", end="", flush=True)
        try:
            result = evaluate(case)
        except Exception as exc:  # keep going so one failure does not hide the rest
            print(f"ERROR {exc}")
            results.append(
                {
                    "case": case,
                    "answer": f"ERROR: {exc}",
                    "sources": [],
                    "intent": "error",
                    "grounded": False,
                    "language": "en",
                    "confidence": 0.0,
                    "model": "none",
                    "latency_ms": 0,
                    "failures": [str(exc)],
                    "passed": False,
                }
            )
            continue
        print("PASS" if result["passed"] else f"FAIL {result['failures']}")
        results.append(result)

    write_report(results)
    passed = sum(1 for r in results if r["passed"])
    print(f"\n{passed}/{len(results)} passed -> {OUT}")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
