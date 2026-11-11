# PlacidWay — Website Knowledge Chatbot

A chatbot that answers visitor questions using only the seven PlacidWay pages it was given, cites
the page behind every answer, and says "I don't know" instead of guessing.

**Live:** https://placidway.patricksamuel.ninja

---

## What it does

A visitor asks *"How much does adenocarcinoma cancer treatment cost in Tijuana?"* and gets:

> The cost for Alternative Adenocarcinoma Cancer Treatment in Tijuana is **$18,995 USD** for the
> Out-Patient Program (3 weeks) and **$30,000 USD** for the In-Patient Program (3 weeks) [1].
> Optional specialized procedures and additional services may incur extra charges [2].

with two source cards underneath, each linking to the page the sentence came from.

Ask *"How much do dental implants cost in Mexico?"* and it says that is not on the pages it can see,
and offers the free quote form. It does not invent a price.

---

## Quick start

```bash
git clone https://github.com/patrickSevans123/placidway-chatbot.git
cd placidway-chatbot

python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

pip install -r requirements.txt
cp env.example .env             # then set LLM_API_KEY

python -m app.ingest            # fetch the 7 pages, build data/corpus.json (~25 s)
uvicorn app.main:app --reload   # http://127.0.0.1:8000
```

`LLM_API_KEY` is the only required setting. `LLM_BASE_URL` accepts any OpenAI-compatible endpoint:
OpenAI, Groq, Together, Ollama, vLLM, or a router.

Docker:

```bash
docker compose up -d --build
curl http://127.0.0.1:8099/api/health
```

---

## How it works

```
                    ┌──────────────────────────────────────────────┐
  visitor message → │ 1. analyse                                   │
                    │    language · intent · standalone query      │
                    └───────────────┬──────────────────────────────┘
                                    │
              ┌─────────────────────┼──────────────────────┐
              ▼                     ▼                      ▼
      out of scope /          retrieve                booking /
      medical advice /    BM25 + dense + RRF          appointment
      → fixed reply       + structured price rows     → fixed reply
                                    │
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │ 2. generate, grounded in numbered sources    │
                    └───────────────┬──────────────────────────────┘
                                    ▼
                    ┌──────────────────────────────────────────────┐
                    │ 3. verify                                    │
                    │    citations exist · every price is in the   │
                    │    evidence · no price in a refusal          │
                    └───────────────┬──────────────────────────────┘
                          pass ─────┴───── fail → regenerate once
                                             → still fail → refuse
```

### 1. Ingestion

`python -m app.ingest` fetches exactly the seven URLs in `app/sources.py`. There is no link
following anywhere in the crawler, so it cannot wander off the allow-list.

The crawler reads `robots.txt` first and obeys it, sends
`PlacidWayAssessmentBot/1.0 (+repo URL; assessment)` as its User-Agent, and waits 3 seconds between
requests — the `Crawl-delay` PlacidWay publishes, which is stricter than the 1 request/second the
brief asks for. Raw HTML is cached under `data/raw/` with a SHA-256 per page, so a refresh only
re-parses pages that actually changed.

Three extraction paths run on each page:

| Path | What it gets | Why |
|---|---|---|
| trafilatura | main article text as markdown | drops nav, cookie banners, related-link rails |
| JSON-LD | `Offer` price + currency, `FAQPage` pairs | the site's own machine-readable claims |
| regex over prose | prices written in sentences | catches "starts at $18,995" with its qualifier |

### 2. Chunking

Section-aware, not fixed-size. The markdown is split on headings, then paragraphs are packed to
about 900 characters with a 150-character overlap. A markdown table is never split — a price table
cut in half is worse than a slightly large chunk. Pages that are a list of headings with one-word
bodies (the video page) are collected into list chunks instead of being dropped as noise.

Result: 183 chunks from 7 pages, mean 524 characters.

### 3. Retrieval

Hybrid, fused with reciprocal rank fusion:

- **BM25** over a lightly stemmed, stop-worded token index, with a synonym map so "cost" also
  matches "price" and "fee".
- **Dense** vectors from `BAAI/bge-small-en-v1.5` via `fastembed` (ONNX, no PyTorch, ~130 MB).
- **RRF** (`k=60`) because BM25 scores and cosine similarities are not comparable.
- A small **page-type prior** on top: a cost question prefers the price list, a clinic question
  prefers the profile. It is a tie-breaker, not a filter.

Dense retrieval is optional. If `fastembed` is missing or the model cannot load, the store falls
back to BM25 alone and `/api/health` reports `dense_retrieval: false`.

### 4. Grounding

Three layers, because a prompt alone does not stop a model from inventing a price.

**Layer 1 — the prompt.** The system prompt states that the numbered sources are the only knowledge
the model has, that every factual sentence needs a `[n]` marker, that prices must keep their
currency and qualifier, and that "I don't know" is a good answer.

**Layer 2 — structured prices.** For cost questions the model is not asked to find a number in a
paragraph. The price rows extracted from JSON-LD and price tables are injected as a separate block,
so the figure it writes is a row it was handed.

**Layer 3 — deterministic checks** (`app/guard.py`), run on every answer:

| Check | Rule | On failure |
|---|---|---|
| Citation | every `[n]` must point at a supplied source; an answer with no citation is rejected | regenerate |
| Numbers | every money amount in the answer must appear in the evidence, after normalising `$18,995` / `18995` / `18,995 USD` | regenerate |
| Refusal | an answer that says the information is missing must not also contain a price | regenerate |

A failed answer is regenerated once with the failure reason appended to the system prompt. If it
fails again, sentences containing unsupported numbers are stripped. If nothing supported remains,
the answer is replaced with the honest fallback. **A wrong price cannot reach the user.**

### 5. Refusal and tricky questions

One small model call classifies the message before retrieval: language, intent, a standalone rewrite
of the question, and any fact the visitor asserted.

| Intent | Handling |
|---|---|
| `out_of_scope` | declines, says what it can help with |
| `medical_advice` | no opinion, no diagnosis, points to their own doctor and the clinic's team |
| `booking` | cannot book, points to the quote form |
| `wrong_premise` | the asserted fact is passed to the generator with an instruction to correct it, not agree with it |
| everything else | retrieval, with a confidence gate |

The confidence gate is the backstop: if the best fused score is below `MIN_RETRIEVAL_SCORE`, the bot
refuses without calling the generator at all. On this corpus, in-scope questions score 0.97–0.99 and
"what is the weather in Cancun" scores 0.09.

### 6. Language and follow-ups

The analyser returns the visitor's language and the answer is written in it, from English sources.
The same call rewrites follow-ups into standalone questions using the last six turns, so *"and what
about recovery time?"* retrieves against the subject of the previous message rather than against
"recovery time" alone.

### 7. Refresh

```bash
python -m app.ingest            # CLI, rebuilds data/corpus.json atomically
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" https://…/api/admin/refresh
```

The endpoint re-crawls, rebuilds the index in place, and returns page/chunk counts. Unchanged pages
are detected by SHA-256 and skipped.

---

## Project layout

```
app/
  config.py     settings from env, every value has a default
  sources.py    the seven URLs, hard-coded
  fetch.py      robots.txt, User-Agent, crawl delay, SHA-256 cache
  extract.py    trafilatura + JSON-LD + price rows + FAQ pairs
  chunk.py      section-aware chunking
  ingest.py     CLI that writes data/corpus.json
  store.py      in-memory BM25 + dense index
  retrieve.py   RRF fusion, page priors, price lookup
  llm.py        OpenAI-compatible client with model fallback
  intents.py    language / intent / standalone query
  guard.py      citation and numeric verification
  answer.py     the pipeline
  db.py         sqlite: history, unanswered log, leads
  main.py       FastAPI routes
web/            index.html, styles.css, app.js — no build step, no CDN
tests/
  run_eval.py   the 12 test cases, writes TEST_RESULTS.md
  test_*.py     unit tests
```

---

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:20128/v1` | any OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | **required** |
| `LLM_MODEL` | `gh/gpt-4.1` | primary model |
| `LLM_FALLBACKS` | `ag/gemini-3-flash,…` | tried in order on error |
| `TOP_K` | `8` | chunks given to the model |
| `USE_DENSE` | `1` | set `0` for BM25-only |
| `MIN_RETRIEVAL_SCORE` | `0.35` | below this, refuse |
| `CRAWL_DELAY` | `3.0` | seconds between requests |
| `ADMIN_TOKEN` | empty | enables `/api/admin/*`; empty disables them |

---

## Deployment

The app runs as a single Docker container behind a Cloudflare Tunnel, so the host needs no open
inbound port and no TLS certificate of its own.

```bash
docker compose up -d --build
# tunnel ingress: placidway.example.com -> http://localhost:8099
```

The container binds to `127.0.0.1` only; the tunnel is the public entry point.

---

## Testing

```bash
pytest tests/                    # unit tests
python -m tests.run_eval         # the 12 assessment cases -> TEST_RESULTS.md
```

`TEST_RESULTS.md` holds the bot's actual answers to the eight questions in the brief plus four extra
cases (Spanish, Arabic, an out-of-corpus treatment, and a policy question), with the automated check
result for each.

---

## Known limitations

- **Seven pages only.** Anything outside them is refused by design. A visitor asking about dental
  implants gets an honest "not on these pages", not a guess.
- **Prices are a snapshot.** The corpus is rebuilt on demand, not on a schedule. A price change on
  the live site is invisible until `python -m app.ingest` runs.
- **The confidence gate is a heuristic.** It separates this corpus well (0.09 vs 0.98) but it is a
  fused-rank score, not a calibrated probability.
- **The numeric guard is exact-match.** It catches an invented price, but it would also reject a
  correct total the model computed by adding two listed prices. That trade-off is deliberate:
  refusing is safer than being wrong.
- **Video pages carry titles, not transcripts.** The bot can say a video exists and link to it; it
  cannot summarise what is said in it.
- **Single process, in-memory index.** Fine for this corpus and this traffic. A larger corpus would
  need a real vector store and a shared cache.
