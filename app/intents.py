"""Work out what the visitor is actually asking before retrieving anything.

One small model call returns four things at once: the language to answer in, the
intent, a standalone version of the question (with pronouns resolved from the
chat history), and any fact the visitor asserted that we should not simply
agree with.

Doing this in one call keeps latency down and keeps the logic in one place. If
the call fails, a rule-based classifier takes over so the bot still works.
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from .llm import LLMError, chat

log = logging.getLogger(__name__)

INTENTS = {
    "cost",
    "comparison",
    "procedure",
    "followup",
    "out_of_scope",
    "medical_advice",
    "booking",
    "wrong_premise",
    "general",
}

ANALYSE_PROMPT = """You classify one message sent to a chatbot for PlacidWay, a medical tourism platform.
The chatbot only knows about one clinic (ITC Immunity Therapy Center in Tijuana, Mexico), three of its
cancer treatment packages, its price list, its videos, and a page comparing alternative medicine prices.

Return ONLY a JSON object with these keys:

"language": ISO 639-1 code of the language the visitor wrote in (e.g. "en", "es", "ar", "fr").
"intent": exactly one of:
  "cost"          - asks a price, cost, fee, or how much something is
  "comparison"    - compares two treatments, clinics, countries or options
  "procedure"     - asks what a treatment is, what is included, how long it takes, recovery, side effects
  "followup"      - refers back to the previous message ("what about...", "and the recovery time?", "why?")
  "out_of_scope"  - unrelated to PlacidWay, clinics, treatments or medical travel (weather, sport, coding, news)
  "medical_advice"- asks whether a treatment is safe, suitable, or right for THEIR personal condition,
                    or asks for a diagnosis, prognosis, or whether they should have surgery
  "booking"       - asks to book, schedule, reserve or confirm an appointment or a date
  "wrong_premise" - states a fact (usually a price or a claim) as if true and asks to confirm it
  "general"       - anything else about the clinic, treatment, travel or the platform
"standalone_query": the question rewritten so it makes sense with no chat history. Resolve pronouns
  and ellipsis using the history. Keep the visitor's own words where possible. If the message is
  already standalone, repeat it unchanged.
"asserted_fact": if the visitor asserted a specific fact (a price, a duration, a claim), copy it here
  verbatim. Otherwise null.

Rules:
- A question about whether a treatment is safe IN GENERAL is "procedure". A question about whether it
  is safe FOR THEM, given their condition or medication, is "medical_advice".
- "I heard it costs $50, is that right?" is "wrong_premise", not "cost".
- If the message is a follow-up, "standalone_query" must contain the subject from the history.

Return JSON only. No prose, no code fences."""


@dataclass
class Analysis:
    language: str
    intent: str
    standalone_query: str
    asserted_fact: str | None = None
    source: str = "llm"


def _history_block(history: list[dict]) -> str:
    if not history:
        return "(no previous messages)"
    lines = []
    for turn in history[-6:]:
        role = "Visitor" if turn.get("role") == "user" else "Bot"
        lines.append(f"{role}: {turn.get('content', '')[:400]}")
    return "\n".join(lines)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("no JSON object in response")
    return json.loads(text[start : end + 1])


def _rule_based(message: str) -> Analysis:
    lowered = message.lower()
    if re.search(r"\b(weather|temperature|forecast|rain)\b", lowered):
        intent = "out_of_scope"
    elif re.search(r"\b(book|schedule|reserve|appointment|tomorrow|next week)\b", lowered):
        intent = "booking"
    elif re.search(r"\b(is it safe for me|should i (have|get)|am i a candidate|my diabetes|my condition|diagnos)\b", lowered):
        intent = "medical_advice"
    elif re.search(r"\b(cost|price|how much|fee|expensive|cheap)\b", lowered):
        intent = "cost"
    elif re.search(r"\b(cheaper|compare|versus|vs\.?|or in)\b", lowered):
        intent = "comparison"
    else:
        intent = "general"
    return Analysis(language="en", intent=intent, standalone_query=message, source="rules")


def analyse(message: str, history: list[dict] | None = None) -> Analysis:
    history = history or []
    messages = [
        {"role": "system", "content": ANALYSE_PROMPT},
        {
            "role": "user",
            "content": f"Chat history:\n{_history_block(history)}\n\nNew message:\n{message}",
        },
    ]

    try:
        result = chat(messages, temperature=0.0, max_tokens=300)
        data = _parse_json(result.text)
    except (LLMError, ValueError, json.JSONDecodeError) as exc:
        log.warning("intent analysis failed (%s); using rules", exc)
        return _rule_based(message)

    intent = str(data.get("intent", "general")).strip().lower()
    if intent not in INTENTS:
        intent = "general"

    language = str(data.get("language") or "en").strip().lower()[:5] or "en"
    standalone = str(data.get("standalone_query") or message).strip() or message
    asserted = data.get("asserted_fact")
    if not isinstance(asserted, str) or not asserted.strip():
        asserted = None

    return Analysis(
        language=language,
        intent=intent,
        standalone_query=standalone,
        asserted_fact=asserted,
        source="llm",
    )
