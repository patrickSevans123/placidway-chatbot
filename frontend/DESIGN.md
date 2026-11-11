# Design notes

The values below are not invented. Each one was read off placidway.com's own
stylesheet or a rendered page and is recorded in `docs/BRAND.md`; this file says
what was used and what was refused. Tokens live in `app/globals.css`, components
in `app/ui.css`.

## Brand values used

| Value | Token | Where it appears |
|---|---|---|
| Coral `#e85a4f` | `--coral` | wordmark, Ask button, citation marks, step dot |
| `#c6474c` | `--coral-ink` | coral that carries small text (4.74:1) |
| `#95202e` | `--coral-deep` | hover on those links |
| `#222` / `#333` | `--ink` / `--body` | headings and the figure / body copy |
| `#555` / `#6a6a6a` | `--muted` / `--faint` | qualifiers and notes (7.4:1, 5.6:1) |
| `#e0e0e0` | `--hair` | every card, panel and table border |
| 10 px / 4 px | `--r-control` / `--r-card` | primary controls and the composer / panels |
| their system stack | `--font` | the whole page, no webfont |
| 15–16 px at 1.55 | `--t-body` | body copy; 600–700 on headings |
| 18 px / 600 white | `.composer-button` | the Ask label, as on their hero CTA |

Coral never carries small text: at 11–15 px the token is `--coral-ink`. Measured
contrast across 103 text-bearing elements at 1280 and 380: no failures, lowest
passing pair 3.5:1 (the 22 px/700 wordmark, a large-text exception).

## Layout decisions

- **Header.** White, hairline underneath, the wordmark set as text in coral, a
  quiet "Treatment guide", and one link out. Their mark is not redrawn or
  hotlinked. Under 600 px the label is dropped rather than allowed to collide
  with the actions.
- **Empty state.** Not a hero. A compact headline, one sentence of what to
  expect, then six bordered cards with thin line icons that submit their own
  question on click. Their page pattern: heading over a row of real choices.
- **The price is the hero.** Figure at 40 px/700 in `#222`, "USD" at 13 px/600
  beside it, the qualifier to its right at 14 px in `--muted`, all on one
  baseline, exactly as their package page prints "Price starting from". Bordered
  hairline panel, 4 px radius, no shadow and no tint. The figure is the only
  display-weight type on the page.
- **Answers are prose.** No bubbles, no tails, no avatar. The question is a
  14 px label above a document-like answer at a 66ch measure.
- **Citations** are coral superscripts, real `#source-N` links, so they work
  from the keyboard and without JavaScript (`:target` lights the card). A click
  scrolls the card into view and gives it a coral left edge and a wash for 2.4 s.
- **Sources** sit in one bordered block shaped like their "About Package" panel:
  a titled header with a hairline under it, then one row per page with its
  title, page type and real URL.
- **Composer.** Fixed to the bottom, white, one hairline, 10 px radius, a coral
  filled Ask button, a textarea that grows to 148 px, and Stop in its place
  while the answer arrives. The page pads its own bottom by the composer's
  measured height, so nothing is ever hidden under it.
- **Trust line** where their accreditations row sits: one quiet sentence, "the
  seven pages, prices checked 11 Nov 2026, not covered we say so". The right
  column lists the seven pages by name, which is the honest equivalent of their
  accreditation badges.

## What the stream does, and what the screen says about it

`stage` drives a two-step line ("Finding the pages" then "Writing the answer"),
shown from the first second. `verifying` is not shown: the server spends about
5 ms in it, so it can never be painted and claiming otherwise would be theatre.
`token` appends, batched to one render per frame. `replace` **swaps** the body —
buffered tokens are dropped and `text` is set to the new answer outright, never
appended. `done` is authoritative.

The guard sends `replace` on nearly every answer, because it collapses repeated
pages and renumbers citations. That is not evidence a figure was removed, so the
page does not claim a correction; it states what is certainly true — "this answer
was checked against the pages before it was shown".

Every state is designed: empty, first token, streaming, verified, refusal
(plain ink, not red), rate-limited with the wait from `Retry-After`, network
error, offline. Each has words, not a spinner.
## Rejected, and why

| Rejected | Why |
|---|---|
| Warm-paper/teal "clinical record" | The brief's premise: it shared nothing with the brand. |
| Their avatar "Alice" | This one says "not on these pages". A face would promise a person who is not there. |
| Their photography | The page sells a reading of seven documents; a stock photo competes with the answer. |
| A gradient hero, icon tiles, shadows | Brand uses white, hairlines and a 10 px radius. Nothing else separates. |
| Chat bubbles | It is a document-grounded reader; the composer is a field. |
| Animated dots, blinking caret | Nothing here animates except the citation wash, and `prefers-reduced-motion` turns that off too. |
| "AI-powered" badge, model name | The reader wants the price and the page, not the machinery. |

`ChatSurface` (state and shell) · `Turn` · `AnswerProse` · `PricePanel` ·
`AnswerFooter` · `Sources` · `States` · `Composer` · `QuoteForm` · `EmptyState` ·
`Header` · `Guide` · `Icons`, with `lib/{brand,lead,stream,price,markdown}`.
