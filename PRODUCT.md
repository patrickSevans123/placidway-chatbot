# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

Two confirmed audiences, both stated in the assessment brief.

**Primary: a patient or family member researching cancer treatment abroad.** They are
anxious, often not a native English speaker, and comparing a clinic in Tijuana against
options at home. Their job: find out what treatment at ITC costs, what a package
includes, who the doctors are, and whether the price is real, without being sold to.
They will ask three to eight questions in one sitting, often as follow-ups.

**Secondary: the Placidway reviewers scoring this build.** They open a public URL, ask
their own questions including hidden ones designed to trip a bot, and then interview the
author for 45 minutes and ask for a small live code change. Their job is to find out
whether the answers are grounded and whether the author understands the code.

## Product Purpose

A question-answering guide to one clinic, built only from the seven PlacidWay pages the
company supplied. It answers price, package, doctor and comparison questions with a
source link on every answer, says "I don't know" when the pages do not cover the
question, and never invents a price, a clinic or a medical fact.

Success: a reviewer asks eight questions, every answer is traceable to a named page,
and the one question the pages cannot answer gets a clear refusal and a route to a
free quote. A small reliable bot beats a larger impressive one that makes things up.

## Positioning

The answer is never separable from its evidence. Every figure on screen carries the
page it came from, and the whole corpus is visible as a list of seven named pages, so a
visitor can see the boundary of what the bot knows before testing it. A generic "ask AI
about healthcare" chat cannot show that boundary, because it has no fixed corpus.

## Operating Context

- The corpus is fixed at seven pages. Crawling beyond them is forbidden by the brief.
- Reviewers test the live URL without installing anything, and the deployment must stay
  up for at least 7 days after submission.
- The 45-minute call includes a live code walkthrough and one small change made on the
  spot, so the code has to be readable by a stranger.
- Prices on the pages change. The UI states the date the prices were last checked.
- The bot is not a medical service. Answers are general information; a doctor is
  recommended for anything clinical.

## Capabilities and Constraints

Confirmed working today, verified against the running app:

- Grounded answers streamed over SSE from `POST /api/chat/stream`, each with cited
  source URLs and a price panel when the corpus holds a price.
- Refusal states for out-of-scope and not-in-corpus questions, with a route to the
  free-quote form (`POST /api/lead`).
- Follow-up questions resolved against chat history.
- A content-refresh path (`/api/admin/refresh`) that re-crawls and rebuilds the corpus,
  with the last check and last change recorded.
- Logging of questions the bot could not answer, exposed at `/api/admin/unanswered`,
  plus aggregate stats at `/api/admin/stats`. **No UI surfaces either today.**
- Health and corpus counts at `GET /api/health`: 7 pages, 183 passages, 69 price rows,
  19 FAQ answers.

Constraints:

- Prices must never be produced from model memory; a price not on a page is reported
  as not listed, with a quote route.
- No secrets in client code. The LLM key stays server-side.
- Crawl rate about one request per second with an identifying User-Agent.
- Frontend ships as a Next.js static export (`frontend/out`) served by FastAPI. The
  `web/` directory is a legacy plain-HTML fallback, not the live app.

Undecided: nothing material for the UI. The brief fixes the corpus, the palette source
and the required features.

## Brand Commitments

- **Name and logo:** "PlacidWay", logo artwork at `frontend/public/placidway-logo.png`,
  used at its 2:1 proportion. The wordmark is coral script and must not be recoloured
  or redrawn.
- **Palette provenance:** every colour must trace to placidway.com's own rendered values
  or declared CSS variables. The accent is their coral; it is a mark, never a field.
- **Voice:** plain, factual, no sales language, no urgency devices. A price is stated
  with its currency and its qualifier; a refusal is stated without apology padding.
- **Non-claims:** no invented testimonials, success rates, accreditations, doctor names
  or prices. The corpus is the only source of facts.

## Evidence on Hand

- `data/corpus.json` — 7 pages, 183 passages, 69 price rows, 19 FAQ answers.
- `data/embeddings.npy` — dense vectors for the corpus.
- `data/app.db` — sessions, messages, leads, feedback, unanswered questions.
- The seven PlacidWay URLs themselves, named in `frontend/app/lib/brand.ts`.
- Two real price tiers from the corpus: out-patient 18,995 USD and in-patient
  30,000 USD, both three-week programmes.
- `TEST_RESULTS.md` — the author's answers to the eight test questions.
- **Absent, and must stay absent:** clinic photography, patient outcomes, doctor
  photographs, review counts, accreditations not in the corpus.

## Product Principles

1. **The evidence is the interface.** A number without its page is a claim; a number
   with its page is an answer. Show the page.
2. **Show the boundary before the visitor tests it.** The seven pages are visible, so
   "I don't know" arrives as a known limit rather than a failure.
3. **Refusal is a feature.** An honest "not on these pages" plus a quote route scores
   higher than a confident guess.
4. **The sheet is not a funnel.** No urgency, no scarcity, no second call to action
   competing with the answer.
5. **Readable by a stranger.** Every screen and every file has to survive a 45-minute
   walkthrough by someone who has never seen it.

## Accessibility & Inclusion

- Target WCAG 2.2 AA. Any text colour pair on the page must clear 4.5:1; the accent
  `#e85a4f` never carries small text.
- The audience includes non-native English readers: short sentences, no idiom, no
  jargon in the interface.
- Keyboard reachable throughout, with a visible focus ring and a skip link; motion
  respects `prefers-reduced-motion`.
