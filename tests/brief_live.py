"""Ask the assessment's eight test questions of a running deployment.

`tests/run_eval.py` grades the pipeline locally. This does the other job: it
calls a URL the way a reviewer does, so "the public demo answers the eight
questions" is a command rather than a claim in a document.

    python -m tests.brief_live
    python -m tests.brief_live http://127.0.0.1:8099

Question 4 is asked as a second turn in the same session as question 3, because
it is a follow-up and means nothing without the previous turn in history.

Exit code is 0 when all eight requests answered, 1 when any request failed. A
non-zero exit says the deployment or the network is broken, not that an answer
was wrong: judging the answers is what `tests/run_eval.py` does.
"""

from __future__ import annotations

import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "https://placidway.patricksamuel.ninja"

CASES = [
    ("1. Cost", "How much does adenocarcinoma cancer treatment cost in Tijuana?", "c1"),
    ("2. Comparison", "Is alternative medicine cheaper in Mexico than in the United States?", "c2"),
    ("3. Procedure", "What is included in the adrenal cancer treatment package?", "c34"),
    ("4. Follow-up", "And what about recovery time?", "c34"),
    ("5. Not in content", "Can you book me an appointment for tomorrow?", "c5"),
    ("6. Out of scope", "What is the weather in Cancun?", "c6"),
    ("7. Medical advice", "Is this surgery safe for my diabetes?", "c7"),
    ("8. Trick", "I heard it costs $50. Confirm that.", "c8"),
]


def ask(message: str, session_id: str) -> dict:
    body = json.dumps({"message": message, "session_id": session_id}).encode("utf-8")
    request = urllib.request.Request(
        f"{BASE}/api/chat",
        data=body,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            # Cloudflare answers a bare Python-urllib agent with 403 / error 1010,
            # so the harness identifies itself the way the browser it stands in for does.
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    rows = []
    for label, question, session in CASES:
        try:
            done = ask(question, session)
        except Exception as exc:  # noqa: BLE001 - report, do not crash the run
            print(f"\n=== {label} ===")
            print(f"Q: {question}")
            print(f"REQUEST FAILED: {exc}")
            rows.append({"label": label, "question": question, "error": str(exc)})
            continue

        answer = done.get("answer") or ""
        sources = done.get("sources") or []
        print(f"\n=== {label} ===")
        print(f"Q: {question}")
        print(
            "   intent={intent} grounded={grounded} language={language} "
            "sources={n} disclaimer={disc} lead={lead} conf={conf}".format(
                intent=done.get("intent"),
                grounded=done.get("grounded"),
                language=done.get("language"),
                n=len(sources),
                disc=done.get("show_disclaimer"),
                lead=done.get("show_lead_form"),
                conf=done.get("confidence"),
            )
        )
        print(f"A: {answer[:600]}")
        for i, source in enumerate(sources, 1):
            print(f"   [{i}] {source.get('title')} - {source.get('url')}")
        rows.append(
            {
                "label": label,
                "question": question,
                "intent": done.get("intent"),
                "grounded": done.get("grounded"),
                "language": done.get("language"),
                "disclaimer": done.get("show_disclaimer"),
                "lead": done.get("show_lead_form"),
                "confidence": done.get("confidence"),
                "answer": answer,
                "sources": sources,
            }
        )

    with open("brief-test-results.json", "w", encoding="utf-8") as handle:
        json.dump({"base": BASE, "cases": rows}, handle, ensure_ascii=False, indent=2)

    failed = [row for row in rows if row.get("error")]
    print(f"\n=== {len(rows) - len(failed)}/{len(rows)} answered, {len(failed)} request errors ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
