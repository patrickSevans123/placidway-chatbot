# PlacidWay — Website Knowledge Chatbot

[![CI](https://github.com/patrickSevans123/placidway-chatbot/actions/workflows/ci.yml/badge.svg)](https://github.com/patrickSevans123/placidway-chatbot/actions/workflows/ci.yml)

A chatbot that answers visitor questions using only the seven PlacidWay pages it was given, cites
the page behind every answer, and says "I don't know" instead of guessing.

**Live:** https://placidway.patricksamuel.ninja

**Test results:** [`TEST_RESULTS.md`](TEST_RESULTS.md) — 24 of 24 cases pass the automated checks,
including the eight questions in the brief and four prompt-injection attempts.

**How to read this repo:** [`docs/CODE_WALK.md`](docs/CODE_WALK.md) is a 45-minute route through the
code. [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) is the request path as one diagram.
[`docs/EVALUATION.md`](docs/EVALUATION.md) is the retrieval measurement, including the result that
did not go my way.

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
Mistral (the default), OpenAI, Groq, Together, Ollama, vLLM, or a router.

The front end is a Next.js static export. `app/main.py` serves `frontend/out` when it exists and
falls back to the original no-build `web/` when it does not, so the API works before the front end
has ever been built:

```bash
cd frontend
npm ci
npm run build      # -> frontend/out, served at /
```

Docker:

```bash
docker compose up -d --build
curl http://127.0.0.1:8099/api/health
```

---

## Stack and why

| Piece | Choice | Why |
|---|---|---|
| Language | Python 3.12 | the ingestion, retrieval and grounding logic stays readable line by line, which is what a code review tests |
| Web | FastAPI + uvicorn | small surface, typed request models, one file of routes |
| Extraction | trafilatura + BeautifulSoup | trafilatura is the strongest open main-content extractor; BeautifulSoup reads the JSON-LD |
| Retrieval | BM25 + `mistral-embed` + RRF | lexical and semantic each cover the other's misses; RRF needs no score calibration. The two evaluations disagree about whether the dense half pays for itself — both numbers are in `docs/EVALUATION.md` |
| Generation | `deepseek-v4-1-flash-1017` via the Mistral API | strong instruction-following on citation rules, ~1 s per answer |
| Storage | JSON corpus + SQLite | no database server to run, and the corpus diff is readable |
| Front end | Next.js 16, static export | React for the streaming UI, but `output: 'export'` means no Node process in production: the files are served by FastAPI exactly like any other static asset |
| Deploy | Docker + Cloudflare Tunnel | one container, no open inbound port, no certificate to manage |

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
brief asks for. Raw HTML is cached under `data/raw/` so the corpus can be rebuilt offline. Change
detection does not use those raw bytes: the live pages carry per-request nonces and rotating
widgets, so their SHA-256 differs on every fetch even when the article is identical. The hash that
decides whether to rebuild is taken over the extracted text instead.

Three extraction paths run on each page:

| Path | What it gets | Why |
|---|---|---|
| trafilatura | main article text as markdown | drops nav, cookie banners, related-link rails |
| JSON-LD | `Offer` price + currency, `FAQPage` pairs | the site's own machine-readable claims |
| regex over prose | prices written in sentences | catches "starts at $18,995" with its qualifier |

trafilatura is pinned to 2.3.1 for a reason. Version 2.0.x returns only the headings of the
price-comparison page — 478 characters instead of 8,916 — which silently shrinks the knowledge base
from 183 chunks to 159 and drops 22 price rows. As a second line of defence, any page over 50 KB
that yields under 1,500 characters of text falls back to a plain body dump.

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
- **Dense** vectors from `mistral-embed` (1024 dimensions) through the same API as the chat model.
  `EMBEDDING_BACKEND=local` switches to `fastembed` with `bge-small-en-v1.5` for offline use.
- **RRF** (`k=60`) because BM25 scores and cosine similarities are not comparable.
- A small **page-type prior** on top: a cost question prefers the price list, a clinic question
  prefers the profile. It is a tie-breaker, not a filter.
- A **treatment-name boost**, because the three packages share almost identical section names and a
  question about the adrenal package must not be answered from the adenocarcinoma page.

#### The two evaluations disagree, and that is written down rather than smoothed over

`tests/retrieval_eval.py` labels 41 answerable and 10 unanswerable questions and measures both
configurations. On that benchmark BM25 wins: hit@8 is 92.7% against 87.8%, and 7 of the 10
unanswerable questions fall below the refusal threshold against 4 of 10 for the hybrid, because
fused dense candidates add vocabulary that inflates the coverage score.

`tests/run_eval.py` measures the thing the product is actually judged on. It scores **24 of 24 with
the dense half on and 22 of 24 with it off**: two comparison questions drop under the refusal
threshold once the extra candidates stop lifting their coverage.

The threshold is calibrated against the hybrid distribution, so the hybrid ships. Reporting both
numbers, and saying which one decided, is more useful than publishing the one that flatters the
system. The open work is named in `docs/EVALUATION.md`: either calibrate the gate per configuration,
or replace coverage-based confidence with an off-topic classifier, which is the honest fix for the
"hair transplant in Istanbul scores 0.86" problem.

### 4. Grounding

Three layers, because a prompt alone does not stop a model from inventing a price.

**Layer 1 — the prompt.** The system prompt states that the numbered sources are the only knowledge
the model has, that every factual sentence needs a `[n]` marker, that prices must keep their
currency and qualifier, and that "I don't know" is a good answer.

**Layer 2 — structured prices.** For cost questions the model is not asked to find a number in a
paragraph. The price rows extracted from JSON-LD and price tables are injected as a separate block,
so the figure it writes is a row it was handed. The block is attached once per page, not once per
chunk, and it is attached whenever the question asks about money — including a follow-up like "and
how much is the inpatient program?", which the intent classifier labels `followup` rather than
`cost`.

Every price answer also carries the date the corpus was built, shown under the sources as
"Prices checked 11 Nov 2026". The pages are a snapshot, and a price with no date reads as if it were
checked this morning.

**Layer 3 — deterministic checks** (`app/guard.py`), run on every answer:

| Check | Rule | On failure |
|---|---|---|
| Citation | every `[n]` must point at a supplied source; an answer with no citation is rejected | regenerate |
| Numbers | every money amount in the answer must appear in the evidence, after normalising `$18,995` / `18995` / `18,995 USD` / `18.995 USD` | regenerate |
| Citation support | a sentence that states a price must cite a page that actually contains that price | regenerate |
| Refusal | a sentence that says the information is missing must not also state a price | regenerate |

The citation-support check is the one that catches a real but misattributed figure. Without it the
bot can quote the correct price and point at the wrong page, which the visitor discovers the moment
they click the link.

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
curl -X POST -H "X-Admin-Token: $ADMIN_TOKEN" "https://…/api/admin/refresh?force=1"
```

A refresh runs in four steps:

1. Fetch the seven pages, obeying robots.txt and the crawl delay.
2. Extract and chunk them in memory. Nothing on disk changes yet.
3. Compare each page's extracted-text hash with the live corpus. If none differ, stop here and
   return `changed: false` — no write, no embedding calls, no index rebuild.
4. Otherwise run the sanity gate, write the corpus atomically, and swap the index in one step.

The sanity gate is the part that matters. It rejects a new corpus and keeps the old one when any
page extracts to under 400 characters, when a single page loses more than half its text, when the
chunk count drops more than 10%, or when the price rows drop more than 10%. This exists because
trafilatura 2.0.0 silently extracted the price-comparison page as 478 characters instead of 8,916,
dropping 24 chunks and 22 price rows with no error at all. `?force=1` bypasses the gate.

On the server a systemd timer runs it daily at 04:17 with a 30-minute random delay:

```bash
systemctl list-timers placidway-refresh.timer
journalctl -u placidway-refresh.service -n 20
```

`/api/health` reports `refresh.last_checked`, `refresh.last_changed`, `refresh.last_result` and
`refresh.changed_pages`, so a quiet day is distinguishable from a broken one.

### 8. Streaming

`POST /api/chat/stream` returns the same answer as `POST /api/chat` as server-sent events: `stage`,
then `token` many times, then optionally `replace`, then `done`.

The hard part is not streaming. It is streaming without breaking the promise that no invented price
is ever shown. The guard runs on the finished text, so anything sent before that point has not been
verified; trimming the guard would trade the criterion the brief weights most heavily for a
cosmetic win.

`app/stream.py` closes the gap. Text is emitted immediately, except a span that could still become a
money mention: a `$` or `US$` with no amount after it yet, or a digit run that is currency-prefixed,
already grouped with separators, or long enough that " USD" may still follow. When the span
completes, its value is compared with the amounts in the evidence the model was given. A match is
released, a mismatch is dropped silently, and the rest keeps flowing. A figure therefore cannot
reach the browser before it has been checked, which is stronger than most streaming chat products
bother to be.

The guard still runs at the end. When it changes the answer — most often because it renumbers
citation markers after collapsing duplicate pages — a `replace` event carries the corrected text and
the browser swaps the message body. `tests/test_stream.py` feeds the filter random chunk boundaries,
because a price split across three tokens is exactly the case a naive implementation leaks.

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
  refresh.py    scheduled refresh: change detection, sanity gate, state file
  store.py      in-memory BM25 + dense index
  retrieve.py   RRF fusion, page priors, price lookup
  llm.py        OpenAI-compatible client, streaming and non-streaming
  intents.py    language / intent / standalone query
  injection.py  prompt-injection and system-prompt-exfiltration screen
  ratelimit.py  in-process sliding window for the endpoints that spend money
  guard.py      citation, numeric and citation-support verification
  stream.py     money hold-back filter and SSE framing
  answer.py     the pipeline, shared by the streaming and non-streaming paths
  db.py         sqlite: history, unanswered log, leads, feedback
  main.py       FastAPI routes
frontend/       Next.js 16 static export (output: 'export'), served by main.py
web/            the original no-build front end, kept as a fallback
tests/
  run_eval.py       24 cases, writes TEST_RESULTS.md
  retrieval_eval.py hit@k and MRR, BM25 vs hybrid
  test_*.py         unit tests
```

---

## Configuration

| Variable | Default | Meaning |
|---|---|---|
| `LLM_BASE_URL` | `https://api.mistral.ai/v1` | any OpenAI-compatible endpoint |
| `LLM_API_KEY` | — | **required** |
| `LLM_MODEL` | `deepseek-v4-1-flash-1017` | primary model |
| `LLM_FALLBACKS` | `mistral-large-latest,mistral-small-latest` | tried in order on error |
| `TOP_K` | `8` | chunks given to the model |
| `USE_DENSE` | `1` | `0` runs BM25 alone; `docs/EVALUATION.md` has both scores |
| `EMBEDDING_BACKEND` | `api` | `api`, `local` (fastembed), or `none` |
| `EMBEDDING_MODEL` | `mistral-embed` | embedding model |
| `MIN_RETRIEVAL_SCORE` | `0.40` | below this, refuse |
| `CRAWL_DELAY` | `3.0` | seconds between requests |
| `RATE_LIMIT_ENABLED` | `1` | limit the two endpoints that call the model |
| `RATE_LIMIT_REQUESTS` | `20` | requests per window, per IP |
| `RATE_LIMIT_WINDOW` | `60` | window length in seconds |
| `ADMIN_TOKEN` | empty | enables `/api/admin/*`; empty disables them |
| `REFRESH_STATE_PATH` | empty | where the refresh history is written; empty means `data/refresh_state.json`. In a container, point it at a volume so a redeploy does not reset it |

---

## Deployment

The app runs as a single Docker container behind a Cloudflare Tunnel, so the host needs no open
inbound port and no TLS certificate of its own.

```bash
docker compose up -d --build
```

Then point a tunnel hostname at `http://localhost:8099`:

```yaml
# /etc/cloudflared/config.yml
ingress:
  - hostname: placidway.example.com
    service: http://localhost:8099
  - service: http_status:404
```

```bash
cloudflared tunnel route dns <tunnel-name> placidway.example.com
```

The container binds to `127.0.0.1` only; the tunnel is the public entry point. `docker compose ps`
and `curl localhost:8099/api/health` are the two checks that matter after a deploy.

Two operational notes learned the hard way:

- **Restarting `cloudflared` drops any SSH session that runs through the same tunnel.** Reconnect
  after the restart rather than assuming the command failed.
- **Cloudflare caches by file extension.** A 404 served once for `/app.js` stays cached at the edge
  after the origin is fixed. The asset links carry a `?v=` query string for exactly this reason;
  bump it when `styles.css` or `app.js` changes.

---

## Testing

```bash
pytest tests/                      # unit tests
python -m tests.run_eval           # the 24 assessment cases -> TEST_RESULTS.md
python -m tests.retrieval_eval     # hit@k and MRR, BM25 vs hybrid -> docs/EVALUATION.md
python -m tests.check_corpus       # the committed corpus is intact
python -m tests.check_secrets      # no credential in a tracked file
```

`TEST_RESULTS.md` holds the bot's actual answers to the eight questions in the brief plus sixteen
extra cases (Spanish, Arabic, four injection attempts with one control, a price freshness check, a
price-list question, a video question, a follow-up that only resolves against the history, and an
out-of-corpus treatment), with the automated check result for each.

CI runs seven jobs on every push:

| Job | What it proves |
|---|---|
| `tests` | 101 unit and HTTP tests, no network |
| `lint` | `ruff check .` is clean |
| `corpus integrity` | the committed corpus has 7 pages, every price has a currency and a source, no chunk over its limit |
| `secrets` | no API key or private key in any tracked file |
| `retrieval benchmark` | hit@1/3/8 and MRR still measure the same with every commit |
| `front end` | `tsc --noEmit`, `next build`, and the export points at `/_next/` |
| `image boots` | the production Docker image starts and answers `/api/health` |

The answer evaluation is deliberately **not** in CI: it calls the model for every question, so it
costs money, needs a key CI does not have, and its score would depend on whichever model that key
points at rather than on the commit.

---

## Known limitations

- **Seven pages only.** Anything outside them is refused by design. A visitor asking about dental
  implants gets an honest "not on these pages", not a guess.
- **Prices are a snapshot.** The corpus is rebuilt on demand, not on a schedule. A price change on
  the live site is invisible until `python -m app.ingest` runs or `POST /api/admin/refresh` is called.
  The corpus is baked into the image, so a redeploy resets it to the version that was built.
- **The confidence gate is a heuristic.** It measures IDF-weighted vocabulary overlap between the
  question and the retrieved evidence, not a calibrated probability. It separates this corpus well
  (0.15 for "weather in Cancun" against 1.0 for a cost question), but a question that reuses the
  corpus vocabulary for a different purpose can slip past it. The model's own instruction to refuse
  is the second line of defence.
- **The numeric guard is exact-match.** It catches an invented price, but it would also reject a
  correct total the model computed by adding two listed prices. That trade-off is deliberate:
  refusing is safer than being wrong. It reads `$18,995`, `18,995 USD`, `18.995 USD` and a bare
  `18,995`; a bare `18995` written with no separator at all is still not treated as money.
- **Streaming shows text before the final guard runs.** The money filter means no unsupported price
  can appear, but a wrong citation marker could be visible for the second before `replace` corrects
  it. That is the cost of streaming at all, and it is bounded to the one thing the filter cannot
  pre-check.
- **A refresh can be triggered, but not scheduled inside the container.** The systemd timer on the
  host is what makes it daily. A different host needs its own timer, or a cron call to the admin
  endpoint.
- **Video pages carry titles, not transcripts.** The bot can say a video exists and link to it; it
  cannot summarise what is said in it.
- **Single process, in-memory index.** Fine for this corpus and this traffic. A larger corpus would
  need a real vector store and a shared cache.
