# Architecture

One process, one in-memory index, seven pages. No vector database, no worker
queue, no message broker.

## One request, end to end

```mermaid
flowchart TD
    A["Browser:<br/>POST /api/chat<br/>{session_id, message}"] --> B["Rate limit middleware<br/>app/main.py<br/>20 requests / 60 s per IP<br/>429 + Retry-After"]
    B --> C["Handler: db.touch_session,<br/>load history, store user turn<br/>app/main.py"]
    C --> D["Injection screen<br/>app/injection.py<br/>current message + every past<br/>user turn; blocked = free refusal"]
    D -->|blocked| R0["Fixed refusal<br/>+ contact card"]
    D --> E["Intent analysis<br/>app/intents.py<br/>model call, JSON out:<br/>intent, language, search_query,<br/>asserted_fact"]
    E -->|out_of_scope / medical_advice / booking| R1["Template reply<br/>no retrieval, no second model call"]
    E --> F["Hybrid retrieval<br/>app/retrieve.py::search<br/>one Index snapshot per request"]
    F --> G1["BM25 over<br/>title + section + text<br/>synonyms expanded<br/>TOP_K / CANDIDATE_K"]
    F --> G2["Dense cosine<br/>mistral-embed<br/>only if dense_ready"]
    G1 --> H["Reciprocal rank fusion<br/>k = 60<br/>+ page-type prior +0.15<br/>+ treatment-term boost +0.06"]
    G2 --> H
    H --> I{"confidence >=<br/>MIN_RETRIEVAL_SCORE<br/>0.40 ?"}
    I -->|no| R2["Deterministic refusal<br/>+ contact card<br/>+ lead form"]
    I -->|yes| J["Structured price rows<br/>app/retrieve.py::price_rows_for_query<br/>label match 2.0, context 0.5,<br/>origin bonus; JSON-LD / table / prose"]
    J --> K["Evidence assembly<br/>app/answer.py::_build_evidence<br/>one numbered block per chunk,<br/>price table appended"]
    K --> L["LLM<br/>app/llm.py<br/>deepseek primary, Mistral fallback,<br/>temperature 0, max 700 tokens"]
    L --> M["Guard<br/>app/guard.py::check<br/>citation present, no phantom source,<br/>every amount in evidence,<br/>amount in the cited block,<br/>no 'missing' + price in one sentence"]
    M -->|issues| N["Regenerate once<br/>stricter system suffix,<br/>issues quoted back"]
    N --> M2["Guard again<br/>then strip unsupported sentences"]
    M2 -->|still failing| R3["Deterministic refusal<br/>+ lead form"]
    M -->|clean| O["Keep cited sources only,<br/>dedupe by URL, remap [n]<br/>to rendered cards"]
    M2 -->|clean| O
    O --> P["200 response<br/>answer, sources, grounded,<br/>intent, confidence,<br/>prices_checked_at"]
```

`prices_checked_at` is `data/corpus.json`'s `built_at` date, and is sent only
when the answer carried price rows (`app/answer.py`, `prices_checked_at=`). It
tells the visitor which snapshot the figures came from, not when the clinic last
changed them.

## Modules

| Module | Responsibility |
| --- | --- |
| `app/main.py` | FastAPI app: routes, rate-limit and cache-header middleware, request logging to SQLite |
| `app/config.py` | Every setting, read once from the environment with a working default |
| `app/sources.py` | The seven allowed URLs and their page types; the only list of pages anywhere |
| `app/fetch.py` | Fetch those seven URLs politely: robots check, delay, on-disk cache in `data/raw/` |
| `app/extract.py` | Turn HTML into clean markdown plus structured price rows and FAQ pairs |
| `app/chunk.py` | Split markdown into ~900-character chunks on headings, keep tables whole |
| `app/ingest.py` | Run fetch, extract and chunk, and write `data/corpus.json` |
| `app/refresh.py` | Re-crawl on a schedule or admin request; refuse a corpus that shrinks too far or loses pages |
| `app/store.py` | Frozen `Index` snapshot: chunks, BM25 matrix, IDF, optional dense vectors; search primitives |
| `app/retrieve.py` | Fuse BM25 and dense with RRF, apply priors, compute confidence, look up price rows |
| `app/intents.py` | Classify one message: intent, language, English search query, asserted fact |
| `app/injection.py` | Block prompt-override and prompt-exfiltration attempts before any model call |
| `app/answer.py` | Assemble evidence, call the model, run the guard, regenerate or refuse, build sources |
| `app/guard.py` | Check citations and every money amount against the evidence blocks |
| `app/llm.py` | OpenAI-compatible chat client with fallback models and a bounded timeout |
| `app/ratelimit.py` | Per-IP sliding window over the two routes that cost money |
| `app/db.py` | SQLite: sessions, messages, leads, feedback, unanswered log, stats |
| `frontend/` | Next.js 16 static export: the shipped UI. Brand values from `docs/BRAND.md`, components in `app/components/`, styles in `app/globals.css` (tokens) and `app/ui.css` |
| `web/` | The original no-build UI, kept as the fallback when `frontend/out` is absent |

## Where two limits live

**Seven pages.** `app/sources.py` holds the tuple `SOURCES`. It is hard-coded and
the crawler in `app/fetch.py` fetches exactly that tuple and follows no links.
Adding a page means editing that file; nothing else discovers pages.

**Corpus rebuild.** `app/refresh.py::run` re-fetches, re-extracts and re-chunks
the seven pages, then calls `check_corpus` before writing. A build is rejected
when fewer than seven pages extract, when any page falls below 400 characters,
when a page loses more than half its characters, when a page that listed prices
now lists none, or when the chunk count or price-row count falls by more than
10% — that is what stops a broken extractor from quietly replacing good content
with a login page. The admin routes
`POST /api/admin/refresh` and `GET /api/admin/refresh/status` expose it, and
`python -m app.ingest` does the same build offline.

The store watches the corpus hash on startup and swaps a complete new `Index` in
one assignment, so a request that takes `store.snapshot` once cannot read chunks
from one build and BM25 scores from another.

## Streaming

`POST /api/chat/stream` is the same pipeline as `POST /api/chat`, with two
differences: the generation step reads the provider's SSE stream, and the text
passes through `app/stream.py::MoneyHoldback` before it is sent.

```mermaid
flowchart LR
    A["_prepare<br/>everything up to the prompt"] --> B["chat_stream<br/>provider SSE"]
    B --> C["MoneyHoldback<br/>hold a span that could<br/>become a money mention"]
    C -->|value in evidence| D["token event"]
    C -->|value absent| X["dropped silently"]
    B --> E["_finish<br/>the same guard as /api/chat"]
    E -->|answer changed| F["replace event"]
    E --> G["done event<br/>sources, metadata"]
```

Events in order: `stage(retrieving)`, `stage(drafting)`, `token` many times,
optional `replace`, `done`. The filter holds back any span that could still
become a money mention and releases it only if its value appears in the evidence.
An unsupported figure is dropped, not shown and retracted.

## What is deliberately not here

- **Semantic cache.** Answers depend on retrieved evidence, and the evidence
  changes whenever the corpus is rebuilt. A cached answer keyed only on the
  question would outlive the price it quotes. A cache keyed on the corpus hash
  is a correct design, and at this traffic it buys nothing.
- **Reranking.** A cross-encoder on 24 candidates would add a second model to
  the critical path for a ranking problem that the evidence shows is caused by
  three near-duplicate package pages, not by a weak re-ranker. Fixing the
  duplicates is cheaper and more predictable. See `docs/EVALUATION.md`.
