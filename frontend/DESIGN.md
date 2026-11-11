# Design notes

The visual system, the references behind it, and the rules the code follows.
Read this with `app/globals.css`, which holds the tokens.

## Research

Refero MCP tools are not set up on this machine, so the research used the
bundled craft references in the `refero-design` skill (typography, color,
motion, anti-ai-slop) plus live reads of the real product:

- PlacidWay.com (the parent site): light page, teal brand, the "Your Way to
  Hope" voice. Kept: the teal, the light ground, the sentence-case voice.
- The ITC package pages (source of the corpus): a price table with an
  out-patient and an in-patient tier. That table, not the chat, is the
  material the answer is actually about.
- The old chat in `web/`: kept the content and the calm refusal, rejected the
  layout (see the brief's review list).

Full Refero style/screen retrieval would deepen this. It was not available, so
every decision below traces to a craft reference, the brief, or the corpus.

## Direction

A price table read like a clinical record. The page is a quiet paper sheet;
the answer is a record with a fixed left margin ruled in hairlines; prices are
figures set in tabular numerals with a hairline under them, the way a receipt
separates a total from its details. Teal is the ink of the record: it marks the
numbered rules, the citation numbers, and the one primary action. Nothing else
uses it.

Locked traits:

- Primary object: the price figure. On a price answer it is extracted from the
  prose into its own block, currency small and before the number, programme
  qualifier after it.
- Measure: prose is capped at 62ch. The empty right third of the sheet is used
  by the right margin, which holds the section index, the note, and the sources.
- Type ramp: 12 / 13 / 15 / 17 / 22 / 28 / 64 with a step always at least 1.2
  and rarely two levels within 2px.
- Radius: 2px on controls, nothing on surfaces. No card shadows.
- Motion: the stage line, the caret, and the one-page open of the index. All
  off under `prefers-reduced-motion`.

## Decision ledger

| Decision | Source | Rule preserved | Why |
|---|---|---|---|
| Hairline record margin instead of chat bubbles | brief + anti-slop #2 "default is not cards" | borders carry function, not decoration | a transcript of boxes reads as a template; a ruled sheet reads as a record |
| Price rule as primary object | brief "price is the primary object" + corpus price table | figure with currency and qualifier | an anxious patient on a phone needs the number before the sentence |
| Teal only for numbers, citations, the one action | color.md accent discipline, anti-slop #8 | one accent, one job | the old UI used teal for link, button, badge and bubble so nothing was primary |
| Right margin rail at ≥1100px | brief "use the dead right third" | asymmetric composition | keeps prose at 62ch without leaving the page half empty |
| System sans stack, no webfont | brief constraint | explicit fallbacks | no CDN font, no vendoring, loads instantly on a phone |
| Refusal in plain ink, no tint | brief "never styled red" | calm, no alarm colour | a dead end is information, not an error |
