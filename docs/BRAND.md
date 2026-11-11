# PlacidWay brand, as it actually ships

There is no public PlacidWay brand guide — a search finds press releases and
partner pages, no style guide PDF. So this file records what the live site
actually uses, taken from `placidway.com` itself rather than guessed. Every value
below was read from their stylesheet or measured on a rendered page.

Source files and pages:

| Where | What it gave |
|---|---|
| `/frontend/includes/new-header/header.min.css` | their theme variables and the coral that carries the brand |
| `/frontend/custom-assets/search-page-chatbot.min.css` | their existing assistant UI ("Alice") |
| `placidway.com/` (rendered, 1280 px) | layout, hero, CTA geometry |
| `placidway.com/package/7903/...` (rendered) | how a price and a trust signal are presented |

## Colour

Their own CSS variables, copied verbatim:

```css
--white:#ffffff; --dark:#3e3e3e; --light-gray:#e9ebeb; --gray:#c4c4c4;
--dark-gray:#b0b0d0; --light-red:#c6474c; --dark-red:#95202e;
--dark-blue:#0b6180; --light-blue:#3a507e;
```

The colour that carries the brand is not a variable: it is **coral `#e85a4f`**.
It appears 11 times in the header stylesheet and 9 times in their chatbot
stylesheet, it is the logo wordmark, the breadcrumb links, the primary button and
the icon accents.

| Role | Value | Where it was measured |
|---|---|---|
| Primary / brand | `#e85a4f` | logo, "Explore Your Options", breadcrumbs, icons |
| Primary hover / dark | `#c6474c` | `--light-red` |
| Deep accent | `#95202e` | `--dark-red` |
| Primary light | `#e98074` | 3 uses in the header |
| Heading ink | `#222222` | section headings at 22px/700 |
| Body ink | `#333333` | body and the `$18,995` price |
| Secondary ink | `#3e3e3e` | `--dark` |
| Navy accent | `#3a507e` (`--light-blue`) | 8 uses in the chatbot CSS |
| Blue accent | `#0b6180` (`--dark-blue`) | links and focus in some modules |
| Hairline | `#e0e0e0` | card and table borders |
| Wash | `#e9ebeb`, `#f1f1f1` | `--light-gray`, table stripes |
| Surface | `#ffffff` | every page background |

Coral on white is 3.05:1 — fine for a 50 px button label at 18 px/600 and for
borders and icons, **not** fine for small body text. Use `#c6474c` (4.31:1) or
`#95202e` when coral has to carry small text.

## Type

They load Roboto from Google Fonts, but the interface font is their variable:

```css
--primary-font: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Oxygen, Ubuntu, sans-serif;
```

Measured sizes on the live pages:

| Element | Size / weight | Colour |
|---|---|---|
| Hero h1 | 46 px / 700 | white on the photo |
| Package h1 | 34 px / 700 | `#222` |
| Section h2 | 22 px / 700 | `#222` |
| Primary button label | 18 px / 600 | white |
| Nav label | 12 px / 400 | `#333` |
| Body | 14 px / 400, line-height 1.5 | `#333` |
| Price figure | 24 px / 700 | `#333` |

## Geometry

- Page container 1140 px with a 1200 px outer frame, 32 px gutters.
- **Primary controls are 10 px radius.** Measured on both hero buttons:
  `Explore Your Options` and `AI Assistant`, 50 px tall.
- Cards and panels are white with a 1 px `#e0e0e0` border and 2–4 px radius.
  Shadows are almost invisible; separation comes from the hairline.
- Their hero search is one white 10 px-radius container holding two inputs split
  by hairlines and two filled buttons at the right, coral then near-black.
- Iconography is thin single-weight line icons at 24–28 px, coral when it marks
  the brand, `#333` in neutral lists.

## How they present a price

This is the pattern to copy, because it is the thing our answers are about. On
the package page, top right of the summary card:

```
Medical Center Reviews
★★★★☆  6 Reviews                    1.5K views
$18,995   Price starting from        ▶
```

The figure is 24 px/700 in `#333`; the words "Price starting from" sit to its
right at 14 px/400 in a muted grey. Deeper in the page the two programmes are
headings: `Included in the Out-Patient Program ($18,995 USD)` at 22 px/700.

So the house convention is **a figure with a quiet qualifier beside it**, never a
bare number and never a large promotional price.

## Trust cues they always show

- Accreditations row: JCI, ISO, COFEPRIS, Turkey MOH, DHCC, NABH, Korea MOHW.
- A named reviewer and a date: "Medically reviewed by Dr. Carlos Bautista on
  Mar 02, 2026".
- Star rating with a review count, and a view count.
- Their own assistant is a named person, **Alice**, presented as a circular
  avatar in a coral pill: "Need help? Chat with Alice".

## Voice

From their own copy: "Your Way to Hope", "Because every patient deserves a way
forward", "trusted care beyond borders". Plain, warm, second person, no
exclamation marks, no marketing superlatives in body copy.

## What this meant for our interface

The front end the brand research replaced was warm paper, near-black ink and
teal — an editorial "clinical record" look that shared no value with PlacidWay.
Rebuilt to brand it is: white surface, coral as the single accent, their system
font stack, 10 px radius on the primary control, hairline-separated white cards,
the figure with a quiet qualifier beside it, and a trust line where their
accreditations row would be.

Two deliberate departures, both defensible in a review:

1. **No avatar, no name.** Alice is a person-shaped marketing assistant. This one
   answers from seven pages and says "the pages do not cover that" — giving it a
   face would promise a person who is not there.
2. **No photography.** Their hero sells a destination. This screen sells a
   reading of seven documents, and a stock photo would compete with the answer.
