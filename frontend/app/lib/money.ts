// `app/guard.py` decides what counts as a money amount when it checks an answer
// against its evidence. The chat uses the same three shapes to decide whether an
// answer talks about money at all, so the price record appears under exactly the
// sentences the guard would police and stays off the answers that never mention
// a figure.
//
//   1. a currency prefix:   $18,995      US$18,995
//   2. a currency suffix:   18,995 USD   thirty thousand dollars
//   3. a bare grouped number: 18,995     18.995
//
// The third form is deliberately narrow: a thousands separator is required, so
// "3 weeks", "24/7" and "2026" are never read as amounts.
const PREFIX = /(?:US\s*\$|\$)\s?\d[\d.,]*/;
const SUFFIX = /\d[\d.,]*\s?(?:USD|usd|dollars?|d[oó]lares?)/;
// No lookbehind: this has to parse in the browsers the page is served to.
const BARE = /(?:^|[^\d.,])(?:\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?|\d{1,3}(?:\.\d{3})+)(?!\d)/;

export function statesAmount(text: string): boolean {
  return PREFIX.test(text) || SUFFIX.test(text) || BARE.test(text);
}
