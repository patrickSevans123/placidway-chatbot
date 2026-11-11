"""Labelled retrieval evaluation: BM25-only versus hybrid, side by side.

No model calls are made for the queries themselves. Dense retrieval still needs
one embedding per question through the configured backend, but that is the same
Mistral embed model that was used to build `data/embeddings.npy`.

The script re-executes itself twice, once with ``USE_DENSE=0`` and once with
``USE_DENSE=1``, because ``app.config`` reads the environment once at import and
``app.store`` builds its index at import time. A single process cannot see both
configurations.

Scoring is at page level, not chunk level: a hit counts when any chunk from a
gold page appears in the top k results, and the chunk's rank is the page's rank.
The corpus holds only seven pages, so a page-level hit is the honest unit for
"could a reader get to the answer".

This is a report, not a gate. Failures are printed because they are the useful
part; the exit code stays 0 unless the script itself breaks.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus.json"

CLINIC = "Clinic profile"
ADENO = "Treatment package"
ADENOCARCINOMA_PAGE = "package-adenocarcinoma"
ADRENAL_PAGE = "package-adrenal"
ANAL_PAGE = "package-anal"
VIDEOS = "Clinic videos"
PRICE_LIST = "Price list"
COMPARISON = "Price comparison"

# Pages are named by slug so a label survives a title edit and can be checked
# against data/corpus.json. Each label was written by reading the chunk that
# contains the answer, not by guessing from a section heading.
SLUGS = {
    "clinic-profile": CLINIC,
    ADENOCARCINOMA_PAGE: ADENO,
    ADRENAL_PAGE: ADENO,
    ANAL_PAGE: ADENO,
    "clinic-videos": VIDEOS,
    "price-list": PRICE_LIST,
    "price-comparison": COMPARISON,
}

C = "clinic-profile"
A = ADENOCARCINOMA_PAGE
D = ADRENAL_PAGE
L = ANAL_PAGE
V = "clinic-videos"
P = "price-list"
X = "price-comparison"


@dataclass(frozen=True)
class Case:
    question: str
    gold: frozenset[str]
    kind: str


def _case(question: str, gold: tuple[str, ...], kind: str) -> Case:
    return Case(question=question, gold=frozenset(gold), kind=kind)


# 41 answerable questions. Gold is the page whose text literally carries the
# answer. Where two pages carry the same fact (the three packages share their
# price table, and the profile repeats it), both are gold: a reader sent to
# either one can answer.
LABELLED: tuple[Case, ...] = (
    # --- cost: package tiers -------------------------------------------
    _case("How much does the out-patient program cost?", (A, D, L), "cost"),
    _case("What is the price of the in-patient program?", (A, D, L), "cost"),
    _case("What does the $30,000 program include?", (A, D, L), "cost"),
    _case("How much is the base package price for alternative cancer treatment?", (C, P), "cost"),
    _case("How much is treatment for breast cancer?", (P,), "cost"),
    # --- cost: add-ons and exclusions -----------------------------------
    _case("How much does the lymphocyte activated killer cells procedure cost?", (A, D, L), "cost"),
    _case("What range do they quote for intratumoral immunotherapy?", (A, D, L), "cost"),
    _case("How much is a blood transfusion if I need one?", (A, D, L), "cost"),
    _case("What does an additional CT scan cost beyond the one included?", (A, D, L), "cost"),
    _case("Is a specialist consultation from an outside surgeon included?", (A, D, L), "cost"),
    # --- cost: comparison page ------------------------------------------
    _case("What is the average cost of alternative medicine abroad?", (X,), "comparison"),
    _case("What price range do clinics quote for alternative medicine?", (X,), "comparison"),
    _case("How much cheaper is alternative medicine abroad than at home?", (X,), "comparison"),
    _case("What hidden costs should I budget for when travelling for treatment?", (X,), "comparison"),
    # --- inclusions ------------------------------------------------------
    _case("How many meals a day are included in the out-patient program?", (A, D, L), "inclusion"),
    _case("Is room and board included in the in-patient program?", (A, D, L), "inclusion"),
    _case("What lab work is done every week during treatment?", (A, D, L), "inclusion"),
    _case("Is imaging like a CT scan or ultrasound included in the price?", (A, D, L), "inclusion"),
    _case("What standard inclusions come with the base package price?", (C, P), "inclusion"),
    # --- duration and itinerary -----------------------------------------
    _case("How long is the treatment program?", (A, D, L), "duration"),
    _case("Why is the treatment period three weeks?", (A,), "duration"),
    _case("What happens in week one of the three-week itinerary?", (A, D, L), "duration"),
    _case("Is there a follow-up consultation after I go home?", (A, D, L), "duration"),
    # --- eligibility -----------------------------------------------------
    _case("Who is eligible for the in-patient program rather than out-patient?", (A, D, L), "inclusion"),
    _case("Can I get treatment if I have a colostomy?", (L,), "eligibility"),
    _case("What determines whether I am accepted for treatment?", (C,), "eligibility"),
    _case("Can I bring a family member with me during treatment?", (L,), "eligibility"),
    # --- clinic and location ---------------------------------------------
    _case("Who founded the Immunity Therapy Center?", (C,), "clinic"),
    _case("Where is the clinic located?", (C,), "clinic"),
    _case("What is the street address of the clinic in Tijuana?", (C,), "clinic"),
    _case("Which doctors work at the clinic in Tijuana?", (C,), "clinic"),
    _case("Is the clinic accredited by COFEPRIS?", (C,), "clinic"),
    _case("How far is the clinic from San Diego airport?", (C,), "clinic"),
    _case("Do they offer free airport rides?", (C,), "clinic"),
    _case("Is the staff bilingual in English and Spanish?", (A,), "clinic"),
    # --- videos and stories ----------------------------------------------
    _case("Are there patient testimonial videos from the clinic?", (V,), "videos"),
    _case("Is there a video of a patient with a breast cancer story?", (V,), "videos"),
    _case("What do patients say in the reviews on the site?", (V,), "videos"),
    _case("Is the treatment gentle and non-toxic according to patients?", (V, C), "videos"),
    # --- medical safety framing ------------------------------------------
    _case("Can alternative treatment be combined with chemotherapy?", (C,), "clinic"),
    _case("What risks should I consider before choosing alternative treatment?", (C,), "clinic"),
)

# 10 questions the seven pages do not answer. A correct system refuses these;
# the confidence gate at MIN_RETRIEVAL_SCORE is what decides.
UNANSWERABLE: tuple[Case, ...] = (
    _case("How much does a dental implant cost in Turkey?", (), "unanswerable"),
    _case("Do you offer a hair transplant in Istanbul?", (), "unanswerable"),
    _case("Can you book me a flight and hotel in Cancun?", (), "unanswerable"),
    _case("What is your refund policy if I cancel after the first week?", (), "unanswerable"),
    _case("Do you accept my Blue Cross Blue Shield insurance?", (), "unanswerable"),
    _case("Is there a doctor who specialises in paediatric leukaemia in Germany?", (), "unanswerable"),
    _case("What is the success rate for stage 4 pancreatic cancer at this clinic?", (), "unanswerable"),
    _case("How do I apply for a Mexican medical visa?", (), "unanswerable"),
    _case("What is the weather like in Tijuana in December?", (), "unanswerable"),
    _case("Who won the football match last night?", (), "unanswerable"),
)

ALL_CASES: tuple[Case, ...] = LABELLED + UNANSWERABLE

TOP_K = 8
HIT_AT = (1, 3, 8)
GATE = 0.40


def _corpus_meta() -> dict:
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    return {
        "built_at": corpus.get("built_at"),
        "page_count": corpus.get("page_count"),
        "chunk_count": corpus.get("chunk_count"),
    }


def _page_slugs() -> dict[str, str]:
    """url -> slug, so hits can be compared with the gold labels."""
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))
    return {page["url"]: page["slug"] for page in corpus.get("pages", [])}


def _evaluate() -> dict:
    """Run every question through the real `search()` and score it."""
    from app.config import settings
    from app.retrieve import search
    from app.store import store

    url_to_slug = _page_slugs()

    answerable: list[dict] = []
    unanswerable: list[dict] = []

    for case in ALL_CASES:
        result = search(case.question, top_k=TOP_K)

        # First rank at which each page appears, from the chunk order.
        page_rank: dict[str, int] = {}
        for rank, hit in enumerate(result.hits, start=1):
            slug = url_to_slug.get(hit.chunk["url"], hit.chunk["url"])
            page_rank.setdefault(slug, rank)

        row = {
            "question": case.question,
            "kind": case.kind,
            "gold": sorted(case.gold),
            "page_rank": page_rank,
            "top_pages": list(page_rank)[:TOP_K],
            "confidence": result.confidence,
        }
        if case.gold:
            hits = {k: any(page_rank.get(slug, 99) <= k for slug in case.gold) for k in HIT_AT}
            first = min((page_rank[s] for s in case.gold if s in page_rank), default=None)
            row.update(hits=hits, first_gold_rank=first, reciprocal_rank=(1.0 / first if first else 0.0))
            answerable.append(row)
        else:
            unanswerable.append(row)

    summary = {
        "dense_available": bool(store.dense_ready),
        "use_dense": bool(settings.use_dense),
        "embedding_backend": settings.embedding_backend,
        "embedding_model": settings.embedding_model,
        "top_k": settings.top_k,
        "candidate_k": settings.candidate_k,
        "gate": settings.min_retrieval_score,
        "answerable": [
            {
                "question": r["question"],
                "kind": r["kind"],
                "gold": r["gold"],
                "page_rank": r["page_rank"],
                "top_pages": r["top_pages"],
                "confidence": r["confidence"],
                "hits": r["hits"],
                "first_gold_rank": r["first_gold_rank"],
                "reciprocal_rank": r["reciprocal_rank"],
            }
            for r in answerable
        ],
        "unanswerable": [
            {
                "question": r["question"],
                "confidence": r["confidence"],
                "top_pages": r["top_pages"],
                "below_gate": r["confidence"] < settings.min_retrieval_score,
            }
            for r in unanswerable
        ],
        "metrics": {
            "n": len(answerable),
            **{f"hit@{k}": sum(r["hits"][k] for r in answerable) / len(answerable) for k in HIT_AT},
            "mrr": sum(r["reciprocal_rank"] for r in answerable) / len(answerable),
            "unanswerable_mean_confidence": (
                sum(r["confidence"] for r in unanswerable) / len(unanswerable) if unanswerable else 0.0
            ),
            "unanswerable_below_gate": sum(r["confidence"] < settings.min_retrieval_score for r in unanswerable),
            "unanswerable_n": len(unanswerable),
        },
    }
    return summary


# ---------------------------------------------------------------------------
# Parent process: run the child in both configurations and print the report.
# ---------------------------------------------------------------------------
def _run_child(use_dense: str) -> dict | None:
    env = dict(os.environ)
    env["USE_DENSE"] = use_dense
    # The dense column needs a backend that can embed the query. If the user has
    # disabled it in the environment, the dense run is expected to report that
    # honestly rather than fall back silently.
    proc = subprocess.run(
        [sys.executable, "-m", "tests.retrieval_eval", "--child"],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if proc.returncode != 0:
        print(f"child run with USE_DENSE={use_dense} failed (exit {proc.returncode})", file=sys.stderr)
        print(proc.stderr[-3000:], file=sys.stderr)
        return None
    payload = [line for line in proc.stdout.splitlines() if line.startswith("RESULT ")]
    if not payload:
        print(f"child run with USE_DENSE={use_dense} printed no RESULT line", file=sys.stderr)
        print(proc.stdout[-2000:], file=sys.stderr)
        return None
    return json.loads(payload[-1][len("RESULT ") :])


def _pct(value: float) -> str:
    return f"{value * 100:5.1f}%"


def _render(bm25: dict, hybrid: dict | None, meta: dict) -> None:
    print("Retrieval evaluation - labelled questions, no answer generation")
    print("=" * 78)
    print(f"corpus built_at   : {meta['built_at']}")
    print(f"corpus            : {meta['page_count']} pages, {meta['chunk_count']} chunks")
    print(f"questions         : {len(LABELLED)} answerable, {len(UNANSWERABLE)} unanswerable")
    print(f"configuration     : TOP_K={bm25['top_k']} CANDIDATE_K={bm25['candidate_k']} "
          f"RRF k=60, gate={bm25['gate']:.2f}")
    print(f"dense model       : {bm25['embedding_model']} via {bm25['embedding_backend']}")
    print()

    columns: list[tuple[str, dict]] = [("BM25 only", bm25)]
    if hybrid is None or not hybrid.get("dense_available"):
        print("HYBRID COLUMN UNAVAILABLE")
        if hybrid is None:
            print("  the USE_DENSE=1 child run did not complete; only BM25 is reported")
        else:
            print(
                "  USE_DENSE=1 was set but the dense index did not load "
                f"(backend={hybrid['embedding_backend']}, dense_ready=False)."
            )
            print("  data/embeddings.npy is gitignored, so this is the expected state on a clean")
            print("  checkout. Run `python -m app.ingest` with LLM_API_KEY set to build it.")
        print()
    else:
        columns.append(("BM25 + dense", hybrid))

    header = f"{'':32}" + "".join(f"{name:>16}" for name, _ in columns)
    print(header)
    print("-" * len(header))

    rows = [f"hit@{k}" for k in HIT_AT] + ["mrr"]
    for label in rows:
        line = f"{label:32}"
        for _, data in columns:
            value = data["metrics"][label]
            formatted = _pct(value) if label.startswith("hit@") else f"{value:5.3f}"
            line += f"{formatted:>16}"
        if len(columns) == 2:
            delta = hybrid["metrics"][label] - bm25["metrics"][label]  # type: ignore[operator]
            line += f"   delta {delta:+.4f}"
        print(line)

    print()
    print("unanswerable questions (gold = empty; the correct behaviour is to refuse)")
    print("-" * 78)
    for _, data in columns:
        m = data["metrics"]
        print(
            f"  mean confidence {m['unanswerable_mean_confidence']:.3f}   "
            f"below gate {m['unanswerable_below_gate']}/{m['unanswerable_n']}"
        )
    print()

    # Per-question table for the hybrid run when it exists, BM25 otherwise.
    shown = columns[-1][1]
    print(f"per-question rank of the first gold page ({columns[-1][0]})")
    print("-" * 78)
    for row in shown["answerable"]:
        rank = row["first_gold_rank"]
        mark = "OK  " if rank and rank <= TOP_K else "MISS"
        print(f"  {mark} {str(rank):>4}  conf={row['confidence']:.2f}  [{row['kind']:<13}] {row['question']}")
    print()

    print("misses: gold page not in the top 8")
    print("-" * 78)
    missed = [row for row in shown["answerable"] if not row["hits"]["8"]]
    if not missed:
        print(f"  none in the {columns[-1][0]} run")
    for row in missed:
        print(f"  Q: {row['question']}")
        print(f"     gold: {', '.join(row['gold'])}")
        print(f"     returned: {', '.join(row['top_pages']) or '(nothing)'}")
        print(f"     confidence: {row['confidence']:.2f}")
    print()

    print("unanswerable questions that would NOT be refused (confidence >= gate)")
    print("-" * 78)
    leaked = [row for row in shown["unanswerable"] if not row["below_gate"]]
    if not leaked:
        print(f"  none in the {columns[-1][0]} run")
    for row in leaked:
        print(f"  conf={row['confidence']:.2f}  {row['question']}")
        print(f"     returned: {', '.join(row['top_pages'])}")
    print()

    if len(columns) == 2:
        print("verdict inputs")
        print("-" * 78)
        for label in rows:
            delta = hybrid["metrics"][label] - bm25["metrics"][label]  # type: ignore[operator]
            verdict = "hybrid ahead" if delta > 0 else ("equal" if delta == 0 else "BM25 ahead")
            print(f"  {label:8} {verdict} ({delta:+.4f})")


def main(argv: list[str]) -> int:
    if "--child" in argv:
        summary = _evaluate()
        print("RESULT " + json.dumps(summary))
        return 0

    meta = _corpus_meta()
    bm25 = _run_child("0")
    if bm25 is None:
        print("BM25 baseline could not run; nothing to report.", file=sys.stderr)
        return 1
    hybrid = _run_child("1")
    _render(bm25, hybrid, meta)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
