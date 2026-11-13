# Design notes

## Reference lock

**Primary direction — a prepared treatment dossier.** One clinic, seven named
source pages, two priced programmes, set as a document rather than a chat window.
White paper, ink rules instead of boxes, mono for every label, numeral and figure,
sans for prose. The answer keeps a margin, the way a prepared document keeps an
apparatus.

| Lock | Value |
|---|---|
| **Preserve** | White ground. Rules, not cards. Right-aligned tabular figures. A 64ch measure with a real margin column beside it. One accent (coral) used only for marks, never as a field. |
| **Borrow only** | GOV.UK table pattern: numbers right-aligned in a column, caption styled as a heading, row rules only. Tufte CSS sidenotes: secondary material (citations) sits in the margin, close to the text, out of the eye's path. |
| **Reject** | The six-card starter grid; a bordered panel for every surface; 4px radius everywhere; a serif/ivory "calm editorial" pass; an indigo or violet accent; a chat bubble; an avatar. |

### Sources

| Source | What was read from it | What it is used for here |
|---|---|---|
| Tufte CSS — <https://edwardtufte.github.io/tufte-css/> | "Sidenotes are like footnotes, except they don't force the reader to jump their eye to the bottom of the page… present related but not necessary information such as asides or citations *as close as possible* to the text that references them… stay out of the way of the eye." | Citations become margin notes: prose in a 64ch measure, the cited pages in a 236px column to its right, sticky, lit by the marker. |
| GOV.UK Design System, table — <https://design-system.service.gov.uk/components/table/> | "When comparing columns of numbers, align the numbers to the right." Table captions "help users find, navigate and understand tables." Row rules, `scope` headers. | The price docket: a `<dl>` of two programmes, figures right-aligned in Plex Mono, a caption set as a label, one 2px ink rule above and one hairline under. No box. |
| IBM Plex — <https://www.ibm.com/plex/> | Drawn for technical documentation; the Mono carries the record-keeping voice, the Sans carries running text. | `IBM Plex Sans` for prose and headings, `IBM Plex Mono` for labels, dates, page numbers and every figure. Self-hosted woff2 in `public/fonts/`. |
| The corpus itself (`data/corpus.json`) | 7 pages, 183 passages, 69 price rows, 19 answers. Out-patient 18,995 USD / in-patient 30,000 USD, both 3 weeks. | Every number on the first screen: the docket, the seven page names, the index totals. |

### Decision ledger

| Decision | Source | Role preserved | Why |
|---|---|---|---|
| Two-tier price docket as the first screen's largest object | GOV.UK numeric table + user brief | Figures right-aligned, rules not boxes | The corpus's own headline fact; a generic RAG demo has no numbers on it at all. |
| Mono for labels, numerals, dates; sans for prose | IBM Plex | Mono = record, sans = reading text | Two type roles give a document its hierarchy without a second display face or a costume serif. |
| Seven named pages as an index, not an accordion | User brief | Contents page | The claim "answers come from seven pages" is only credible if you can see the seven. |
| Index only on the empty screen | User brief (panel is filler) | — | Once a question is asked the margin belongs to the citation apparatus, and the answer gets the full width. |
| Answer in a 64ch measure with a 236px margin column | Tufte CSS | Sidenote: secondary, adjacent, out of the reading path | The marker and the page it points at are visible at the same time; no jump to a panel below. |
| Rules instead of card borders on the docket, sources and notices | GOV.UK table + anti-slop "cards are not default" | Row rules | Kills the uniform "white box with a 1px border" that made every surface equal. |
| One grey block (#f5f5f5, their token) — the contents column, square corners | Their own light section background | Section tint, not a card | Gives the opening one tonal block against white paper, so the page has two materials, not five. |
| Coral only as a mark: the eyebrow tick, citation glyphs, the Ask fill, the lit note edge | Their palette; measured #c6474c for text and fill | Accent-only, AA | #e85a4f is 3.05:1 on white and never carries text; coral-ink is 4.77:1. |
| Single staggered reveal on the opening (eyebrow → title → docket rule → list) | Craft rule: high-impact moment, one only | — | The page is static after; the answered state does not animate on arrival. |
| No photography | User constraint | — | There is no honest picture of this clinic; the numbers are the picture. |

---

## Palette

Every value below was read off placidway.com: computed values over a rendered
page at 1280, and the colours declared in their CSS variables. Tokens in
`app/globals.css`, components in `app/ui.css`.

| Token | Value | Where it was measured |
|---|---|---|
| `--coral` | `#e85a4f` | rendered accent, 6 elements; the logo artwork |
| `--coral-ink` | `#c6474c` | their `--light-red`; filled buttons |
| `--coral-deep` | `#95202e` | their `--dark-red`; hover, disabled label |
| `--coral-wash` | `#fdefee` | rendered coral wash, 5 elements |
| `--coral-line` | `#f6d5d2` | derived: `#e85a4f` at 28% over white |
| `--surface` | `#ffffff` | page background, 164 elements; `theme-color` |
| `--wash` | `#f5f5f5` | their light section background, 11 elements |
| `--wash-2` | `#f8f8f8` | their second light background, 6 elements |
| `--ink` | `#222222` | their dark heading colour, 35 elements |
| `--body` | `#333333` | their body colour, 623 elements |
| `--muted` | `#555555` | their secondary text, 92 elements |
| `--faint` | `#6a6a6a` | not theirs: their `#777` darkened, 4.48 -> 5.6:1 |
| `--hair` | `#e9ebeb` | their `--light-gray`, now the border colour |
| `--hair-strong` | `#c4c4c4` | their `--gray` |

Contrast, on the two grounds this page now has:

| Pair | Ratio | Use |
|---|---|---|
| `--ink` on white | 15.9 | headings, figures |
| `--body` on white | 12.6 | prose |
| `--muted` on white | 7.4 | qualifiers, notes |
| `--faint` on white | 5.6 | meta, urls |
| `--coral-ink` on white | 4.77 | citation glyphs, filled buttons' ground |
| white on `--coral-ink` | 4.77 | Ask, primary buttons |
| `--muted` on `--wash` | 6.8 | labels in the contents column |
| `--faint` on `--wash` | 4.96 | counts, urls there |
| `--coral-deep` on `--wash` | 7.6 | the one coral mark on grey |

Rules that follow from the table: `--coral-ink` never sits on `--coral-wash`
(4.27) nor on `--wash` (4.38). On those grounds coral text is `--coral-deep`.
`--coral` (#e85a4f, 3.05) never carries text at all; it is a dot, a rule or a
border.

`#777` never carries text (4.48:1). The slate family (`#1d2b33`, `#24353e`,
`#16222a`, `#3a507e`, `#0b6180`) is still not used.

## Type

Self-hosted, no build-time network, no runtime dependency:

| File | Use |
|---|---|
| `public/fonts/plex-sans-latin.woff2` | 38 KB variable, weights 400–600, prose and headings |
| `public/fonts/plex-mono-{400,500,600}.woff2` | 14–15 KB each, labels, figures, dates, page numbers |
| `public/fonts/OFL.txt` | the SIL Open Font License 1.1 the files ship under, copied from `IBM/plex` |

IBM Plex is licensed under the SIL OFL 1.1 (Copyright 2017 IBM Corp., Reserved
Font Name "Plex"), so the licence travels with the files in `public/fonts/`.

Scale (seven sizes, one ratio each side of body):

| Token | Size | Role |
|---|---|---|
| `--t-figure` | `clamp(34px, 4.4vw, 46px)` | the price, the one display object |
| `--t-display` | `clamp(27px, 3.1vw, 36px)` | the opening headline |
| `--t-title` | 20px | panel and notice titles |
| `--t-lead` | 17px | the lede, the question line |
| `--t-body` | 16px | prose |
| `--t-small` | 13px | notes, meta |
| `--t-label` | 11px | mono captions, uppercase, `0.1em` tracking |

All caps text always carries `letter-spacing`. Figures are `tabular-nums`.

## Layout

**Superseded by "Chat surface" below, kept as the record of the first build.** The
composer is no longer fixed, there is no contents column, no margin notes and no
opening docket; the answer is a block in a thread, not a two-column spread.

- **Header.** 71px with their 2:1 logo at 123x62 (104x52 under 600), a hairline
  rule, a quiet "Treatment guide", and one link out. No second bar.
- **Opening.** Two columns at ≥1040: dossier on the left, contents on the right.
  Eyebrow, headline, one sentence, the docket, then three questions as rows. The
  contents column is the only tinted surface on the page.
- **The docket.** `<dl>`, two rows, 2px ink rule on top, hairline between the
  rows, figures right-aligned in mono at display size, one note underneath.
- **The answer.** Two columns at ≥1180: a 64ch measure and a 236px margin. The
  question is a numbered line at 17px in ink, not a grey label.
- **Citations** are real `#source-N` links, mono, coral-ink, superscript;
  `:target` lights the note without JavaScript.
- **The margin notes.** Sticky, top-aligned, numbered, hairline-separated, no
  box. The lit note takes a coral-wash ground and a 2px coral edge — a status
  mark, not decoration.
- **Composer.** Fixed, white, one hairline, page padded by its measured height.

## Corrections after review

Each of these came from reading the built page, not from the reference lock.

| What was wrong | What changed | Why |
|---|---|---|
| The headline read "…and what the seven pages say" — pipeline jargon, and it repeated "ITC" from the eyebrow | "What cancer treatment at ITC costs." The source claim moved to the lede: "Answers are written only from the seven PlacidWay pages each one cites." | The first screen should say what the product is about, not how it works. |
| The headline broke after "cancer", leaving "at" dangling | `text-wrap: pretty` and `max-width: 11em` (396px at 36px): between "What cancer treatment" (369px) and that line plus " at" (408px) | Measured both candidates; `balance` produced the worse split. |
| The disclosure sat between two rules in 11px caps, so it read as a section heading | Sentence case, 12px, no rule under it; the page's mono labels stay uppercase and stay between rules | Labels and controls are different objects and should not look alike. |
| The bottom of the page had two rule + line pairs 40px apart | The status line lost its rule and its leading, so it reads as a footnote to the trust line | One band, not two. |
| "7 pages indexed · ready to answer" repeated the contents column and the trust line | "Answer service ready" | Say it once. |
| An off-topic answer was rendered as a normal answer, with "checked against the pages" and "From 0 pages · Answered in – s" | A boundary notice: "Outside these pages", the model's apology, one line saying what the guide does cover; no check line, no provenance | Nothing was cited, so nothing was checked. The old state claimed otherwise in two places. |
| An answer that said "please request a free quote" had no quote control, because `show_lead_form` was false for a `general` intent | The control follows the words: if the answer asks for a quote, the quote control is rendered | A sentence pointing at a button that is not on the page is worse than no sentence. |

## What the stream does

`stage` drives a two-step line; `verifying` is never shown (about 5ms on the
server). `token` appends, batched to one frame; `replace` **swaps** the body;
`done` is authoritative. Nearly every answer gets replace, which is not evidence
a figure was removed, so the page says only that the answer was checked.

## Rejected

Their photography, a gradient hero, a blinking caret, a second accent for page
types, chat bubbles, an avatar: each competed with the answer or the coral
markers. A serif+ivory editorial pass was rejected because the corpus is a price
schedule, not an essay, and because it is the current default look of generated
design. The right-hand panel was kept only as a contents column and only before
the first question: repeating the page count beside every answer was filler.

## Sleek pass

Read off the built page at 1440 and 390. The direction did not change: the same
dossier, the same tokens, one accent. What changed is how much of each system is
on screen at once.

The token and control decisions below still hold. Two rows describe the shell as it
was before the chat rewrite: the margin note, and the fades that hid the edges of a
fixed composer. Neither exists now.

| What was wrong | What changed |
|---|---|
| Six hairlines of one weight plus a 2px ink rule per screen, so nothing ranked | Exactly two: `--rule` (#e7e7e4) for every divider, `--rule-ink` (#1f1f1f) at 2px for the docket's top rule only. Field edges use `--rule-field` (#b4b4b0), which is not a divider. Rules were deleted where they separated one-line blocks: the docket caption, the starters heading, the contents label, the contents footer, the sources heading, the figure, the answer footer. |
| The docket's unit floated at an arbitrary height | `--figure-cap: 0.698` is Plex Mono's measured cap height at the figure size. The unit is 12px, weight 400, `--faint`, 7px away, and its baseline is lifted `0.698em` onto the figure's cap line. Measured: the unit's optical top (8.376 + 2.4 + 0.62) lands on the figure's ink top within 0.1px. |
| The Ask button was a coral wash that read disabled | Solid `--coral-ink` with white (4.77:1), 3px radius, `--coral-deep` on hover. Disabled is the same coral at 60% opacity, not a second colour. The field is white with a `--rule-field` edge that turns `--ink` on focus; the wash and glow are gone. |
| Boxed thumbs and a boxed copy control competed with the answer | One 12px row: `Copy · Helpful? [Yes] [No]`, no boxes, one hairline separator between copy and the rating, `--muted` at rest and `--ink` on hover. The provenance line keeps its facts in `--faint`. |
| Six uppercase 11px labels a screen at 0.1em | One style: 10.5px, 0.14em, `--faint`, used only where a label names a block. The refusal lead became a title, because it named no block. |
| The margin note cut a URL mid-word (`/Alte…`) | The note shows the domain, whole; the full address is in `title`. The package slug is one unbreakable 324px word in a 194px column, so no shortening of it can end on a word boundary. |
| A one-pixel pipe between the logo and its label | Removed. The label is the page's label style. |
| Nothing answered the pointer | One 160ms `--ease` tick everywhere: the question row moves its arrow 3px and draws the title underline, buttons darken, links draw their underline in ink, the source row draws its title underline. Under `prefers-reduced-motion` the colours change and nothing slides. |

Rejected in this pass: a gradient (tried for the rating separator, removed), a
second accent, and rewriting `readableUrl`, which lives outside the files this
pass covered.

### Two corrections after reading the build

| What was still wrong | What changed |
|---|---|
| Content was sliced on a hard line where it met the fixed composer, and again where it met the sticky masthead — it read as cut off, not as continuing | Both edges dissolve into the page ground instead: a 36px white fade above the dock and a 20px one below the masthead. The dock lost its border, since the fade is now the edge. |
| The composer placeholder repeated the lede sentence word for word | "Type a question". The lede already says what can be asked. |
| Separators were drawn before each item, so a wrapped line could begin on a stranded dot | `provenance` and the trust line draw the dot after the clause before it, and the trust line is two spans so it wraps as clauses, not mid-phrase. |

## Chat surface - redesign of 13 Nov 2026 (current)

**Supersedes the answer desk below.** The palette provenance, the two type roles,
rules-not-cards and coral-as-a-mark are kept exactly. What is replaced is the
anatomy: the page is a conversation, not a document. The first version of this
redesign was a two-column desk with a standing evidence rail; it was rejected
because it did not read as a chatbot, and the rail is what caused it.

### Shell

`.shell` is a `100dvh` grid of three rows: the bar (`auto`), the thread (`1fr`),
the dock (`auto`). Nothing else scrolls.

- `.thread` is the **only** element between the conversation and the document
  with a computed `overflow-y` that is not `visible`. The bar and the dock are
  rows of the same grid, so neither can cover a line of an answer, and the last
  element of the last turn always sits above the top edge of the composer.
- `body { overflow-x: clip }`, never `hidden`: `hidden` on one axis turns the
  other into `auto` and makes the body a second scroll container.
- The conversation column is `--column: 660px`, about 85 characters at 16px.
  `--page: 1088px` stays defined because `admin.css` reads it as
  `var(--page, 900px)`; the chat does not use it.

This replaced a nested pane that clamped the document to the viewport. Measured
before that fix, on an answered turn at 1440x900: the document was 900px tall and
could not scroll, `.read` clipped 174px of the answer, and 150px of the price
record was reachable only through a 4px inner scrollbar.

### Type and colour

IBM Plex Sans for anything read as a sentence, IBM Plex Mono for anything read as
a record (labels, counts, figures, dates, the service line). Coral `#c6474c` is a
mark only: a 5px square, a citation glyph, the column rule beside a disclaimer. It
is a field only on the one filled button.

Rules, not card borders: hairlines (`--rule`) divide, a 2px `--rule-ink` line marks
the one structural break in a region, and fields carry a `--rule-field` edge that
turns ink on focus.

Radii: `--r-control` 3px on every field, button and chip. `--r-bubble` 12px belongs
to the question alone.

### The turn

- The question is a bubble, right-aligned, `--wash` ground, 12px radius, its
  bottom-right corner pulled back to 3px. It is the only filled, rounded object on
  the page: the visitor is speaking.
- The answer is a full-width block on white. It carries citations, so it cannot be
  a bubble.
- Answer order: prose, the checked line, the disclaimer when `show_disclaimer` is
  true, the copy/rating row and provenance, the `Sources - N pages` disclosure, the
  package price record, and the quote form when the answer asks for one.
- Consecutive citation markers are separated by a comma in the same raised mono
  (`1,3`). Without it the model's `[1][3]` rendered as "13", which reads as
  footnote thirteen; three adjacent markers rendered as "321".
- The price record renders only when that answer's own text states an amount, using
  the three shapes `app/guard.py` polices (currency prefix, currency suffix, bare
  thousands-grouped number). It is an appendix to a price answer, not a fixture on
  every answer.

### Sources

A native `<details>` whose `open` is mirrored from state. Clicking a superscript
citation both lights the page row and forces the disclosure open, so the light is
never scheduled into a closed box. The summary is also a control in its own right:
the reader can open the list without touching a citation.

### Persistence

`sessionStorage["placidway.chat.v1"]` holds `{sessionId, turns}` as one value,
written when an answer settles and removed when both halves are gone. Restore
either takes both or clears the key; a turn that was still streaming when the tab
closed is restored as stopped. "New conversation" clears both. Keeping the id but
not the turns, as an earlier build did, meant a follow-up was answered from a
conversation the reader could not see.

### The empty screen

A greeting, one sentence naming the boundary (general information, not medical
advice), three questions stacked as full-width rows that send on a single click,
and one mono line with the corpus counts and the date the prices were checked. The
composer is focused on arrival and its placeholder names what can be asked without
repeating the greeting.

### Removed in this pass, and why

| Pattern | Reason |
|---|---|
| The seven-page evidence rail | A standing corpus panel beside the conversation is what made the page read as a document. The same information now lives in the per-answer disclosure and the empty screen's count line |
| The opening price docket | The price record travels with the answer that needs it |
| The permanent footer disclaimer | It repeated one line on every answer, which the brief forbids; the disclaimer is now per answer and driven by `show_disclaimer` |
| The fixed composer | It covered starter rows and forced a nested scroller. The dock is a grid row, so it cannot |
| Eyebrow above the headline, `01`-`07` page numbering | Kickers and numbers that encode no sequence |
| `lib/price.ts` and the parsed price | It extrapolated figures out of model prose. Deleted; the record prints the corpus's own two tiers and links the page |

### Measured after the rebuild

At 1440x900 and 390x844 on a thread with one answered procedure question: exactly
one scroll container (the thread); thread 732/732 at 1440 and 1304/676 at 390 with
`scrollTop` driven to the end on send; the last element of the turn at 694 against a
composer top of 809; document `scrollWidth` equal to `clientWidth` at both widths.
The disclaimer renders in a `procedure` answer and not in a `cost` answer.

### Operations route

`/admin/` is a second static route, token-gated at the browser. The admin token is
typed by the operator, held in `sessionStorage`, and never enters the bundle, a URL
or a log line, because the backend protects those endpoints and the public page must
carry no secret. It reads `/api/health` without a token to show the corpus before
connecting, then unlocks three panels: the corpus and its last refresh with a run
control, the questions the bot could not answer grouped by question text, and the
session totals.

### Files

`ChatSurface` (state, shell, persistence) -> `Turn` -> `AnswerProse` -> `PricePanel`
-> `AnswerFooter` -> `Sources` -> `States` -> `Composer` -> `QuoteForm` ->
`EmptyState` -> `Header`, with `lib/{brand,lead,stream,markdown,money,types}`.
The operations route adds `admin/page.tsx`, `admin/admin.css` and `lib/admin.ts`.
Deleted across both passes: `Contents.tsx`, `EvidenceRail.tsx`, `lib/price.ts`.

Tokens in `app/globals.css`, components in `app/ui.css`, route-local styles in
`app/admin/admin.css`. Self-hosted Plex only; no new dependency.
