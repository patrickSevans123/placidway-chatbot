# Design notes

Every colour below was read off placidway.com: computed values over a rendered
page at 1280, and the colours declared in their CSS variables. Tokens in
`app/globals.css`, components in `app/ui.css`.

## Logo and icon

Their image CDN serves the artwork cropped at quality 85 (420x211, `#e85a4f` on
transparency, ink box flush to the edges). From their 1850x931 original, cropped
to the ink box and resampled with Lanczos: `public/placidway-logo.png` 246x124 and
`placidway-logo@2x.png` 493x248. Nothing is redrawn, traced or hotlinked.

It renders at 123x62 at 1280 (their `<img>` is 140x70 in a 70px bar, 2:1) and
104x52 under 600px, with `width`/`height` attributes, `alt` "PlacidWay",
`decoding="async"`, `fetchpriority="high"` and a 1x/2x srcset. The bar went from
60px to 70px, their height. Image aborted, then loaded: header 71px both times,
0px shift, at 1280 and 380; on a 380 screen the actions still end at 364.

The icon is their official square app icon (`pw-192`, `pw-512`), not the coral
wordmark: it is drawn to survive 32px, its background is opaque so iOS has
something to round, and the wordmark at that size becomes a smear. Shipped as
`favicon-32.png`, `apple-touch-icon.png` (180, from the 512) and `icon-192.png`,
declared through `metadata.icons`; `themeColor` stays `#ffffff`.

## Palette

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

What changed: `--coral-wash` `#fdf1f0` -> `#fdefee` (2 steps on every channel),
`--wash` `#f1f1f1` -> `#f5f5f5` (+4), `--wash-2` `#f7f7f7` -> `#f8f8f8` (+1),
`--hair` `#e0e0e0` -> `#e9ebeb` (+9 red, +11 green, +11 blue). `--coral-wash` is
now also the disabled Ask fill, replacing a hand-picked `#fdeceb`. Filled buttons
moved from `#e85a4f` to `#c6474c`: white on the bright coral is 3.05:1 and fails
AA at both sizes used (15px/600, 18px/600); white on `#c6474c` is 4.77:1.
Measured in the two states the page check never visits: Ask enabled 4.77, quote
form open 4.77.

`#777` never carries text (4.48:1). `#a4b4ba` and `#7c8f96` are footer text on
their dark slate only. The slate family (`#1d2b33`, `#24353e`, `#16222a`,
`#3a507e`, `#0b6180`) is not used: at 12px a navy page-type label inside an
otherwise grey source list became the only cool hue on the page and pulled the
eye off the coral citation marks, the one thing that must be found.

## Layout

- **Header.** White, hairline under it, their logo, a quiet "Treatment guide" and
  one link out. Under 600px the label is dropped and the logo steps down.
- **Empty state.** A compact headline, one sentence, six bordered cards with line
  icons that submit their own question.
- **The price is the hero.** 40px/700 in `#222`, "USD" 13px/600 beside it, the
  qualifier 14px in `--muted`, one baseline, hairline panel, no shadow.
- **Answers are prose.** A 14px question label above a document at 66ch.
- **Citations** are coral superscripts, real `#source-N` links, so they work from
  the keyboard and without JavaScript (`:target` lights the card).
- **Sources** in one bordered block shaped like their "About Package" panel.
- **Composer.** Fixed, white, one hairline, a filled Ask button, Stop while the
  answer arrives, page padded by its measured height.

## What the stream does

`stage` drives a two-step line; `verifying` is never shown (about 5ms on the
server). `token` appends, batched to one frame; `replace` **swaps** the body;
`done` is authoritative. Nearly every answer gets replace, which is not evidence
a figure was removed, so the page says only that the answer was checked.

## Rejected

Chat bubbles, an avatar, their photography, a gradient hero, a blinking caret and
a second accent for page types: each competed with the answer or the coral marks.
The page is a reading of seven documents, so the design stays a document.

`ChatSurface` (state and shell) · `Turn` · `AnswerProse` · `PricePanel` ·
`AnswerFooter` · `Sources` · `States` · `Composer` · `QuoteForm` · `EmptyState` ·
`Header` · `Guide` · `Icons`, with `lib/{brand,lead,stream,price,markdown}`.
