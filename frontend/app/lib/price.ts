// The price figure is the primary object on a price answer, so it is lifted out
// of the sentence and set on its own. Nothing here invents a figure: the value,
// the currency, the qualifier and the citation all come from text the backend
// already verified.
//
// The rule is deliberately narrow. A figure is lifted only when the sentence it
// sits in also names a programme, a package or a duration. An add-on price, a
// range, or an average with no qualifier stays in the prose where it was
// written, so the screen never promotes a stray number to "the price".

export interface PriceLine {
  amount: number;
  currency: string;
  /** "The out-patient programme", "The package price", "Starting from, the 3-week programme" */
  qualifier: string;
  /** The `[n]` marker of the sentence the figure came from, so the figure cites the same page. */
  cite: number | null;
  /** Character offset of the figure, so the prose can drop exactly its own sentence. */
  at: number;
}

const SYMBOL_TO_CODE: Record<string, string> = { "US$": "USD", $: "USD", "€": "EUR", "£": "GBP" };

const PREFIXED = /(US\$|\$|€|£)\s?(\d[\d.,]*)/g;
const SUFFIXED = /(\d[\d.,]*)\s?(USD|EUR|GBP|dollars?)/gi;
const BARE = /(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d{1,2})?)(?![\d,])/g;
const CITE = /\[(\d{1,2})\]/;

const WORD_NUMBER: Record<string, string> = { two: "2", three: "3", four: "4", five: "5" };
const DURATION = /\b(\d|two|three|four|five)\s?-?\s?(?:week|wk)\b/i;
const STARTS = /\bstart(?:s|ing)?\s+(?:at|from)\b/i;

interface Mention {
  start: number;
  end: number;
  value: number;
  currency: string | null;
}

function parseAmount(raw: string): number | null {
  const trimmed = raw.replace(/[.,]+$/, "");
  // 18,995 / 18.995 / 15032 — a dot is a thousands separator only when it
  // groups exactly three digits, which is what the Spanish answers write.
  const normalised = /^\d{1,3}(?:\.\d{3})+$/.test(trimmed)
    ? trimmed.replace(/\./g, "")
    : trimmed.replace(/,/g, "");
  const value = Number(normalised);
  return Number.isFinite(value) ? value : null;
}

/** Every figure in the text, left to right, overlaps removed. */
function mentions(text: string): Mention[] {
  const found: Mention[] = [];

  for (const m of text.matchAll(PREFIXED)) {
    const value = parseAmount(m[2]);
    if (value === null) continue;
    found.push({
      start: m.index ?? 0,
      end: (m.index ?? 0) + m[0].length,
      value,
      currency: SYMBOL_TO_CODE[m[1]] ?? "USD",
    });
  }
  for (const m of text.matchAll(SUFFIXED)) {
    const value = parseAmount(m[1]);
    if (value === null) continue;
    found.push({
      start: m.index ?? 0,
      end: (m.index ?? 0) + m[0].length,
      value,
      currency: m[2].toUpperCase() === "DOLLARS" ? "USD" : m[2].toUpperCase(),
    });
  }
  // A bare grouped number ("18,995") is how a sentence states a package price
  // when the currency was named once, earlier.
  for (const m of text.matchAll(BARE)) {
    const value = parseAmount(m[1]);
    if (value === null) continue;
    found.push({ start: m.index ?? 0, end: (m.index ?? 0) + m[0].length, value, currency: null });
  }

  found.sort((a, b) => a.start - b.start || b.end - a.end);
  const kept: Mention[] = [];
  for (const mention of found) {
    if (kept.some((other) => mention.start < other.end)) continue;
    kept.push(mention);
  }
  return kept;
}

/** The sentence around one span, bounded by punctuation or a line break. */
function sentenceAround(text: string, start: number, end: number): string {
  const boundary = /[.!?\n]/;
  let left = start;
  while (left > 0 && !boundary.test(text[left - 1])) left -= 1;
  let right = end;
  while (right < text.length && !boundary.test(text[right])) right += 1;
  return text.slice(left, Math.min(right + 1, text.length)).trim();
}

/** The label a sentence earns, or null when the figure is not a package price. */
function qualifierFor(sentence: string): string | null {
  const parts: string[] = [];
  if (STARTS.test(sentence)) parts.push("Starting from");

  if (/\bout[\s-]?patient\b/i.test(sentence)) parts.push("the out-patient programme");
  else if (/\bin[\s-]?patient\b/i.test(sentence)) parts.push("the in-patient programme");
  else if (/\bpackage\b/i.test(sentence)) parts.push("the package price");
  else {
    const duration = sentence.match(DURATION);
    if (duration) {
      const count = WORD_NUMBER[duration[1].toLowerCase()] ?? duration[1];
      parts.push(`the ${count}-week programme`);
    }
  }

  return parts.length ? parts.join(", ") : null;
}

export function extractPrice(answer: string): PriceLine | null {
  const text = answer.replace(/\*\*/g, "");

  for (const mention of mentions(text)) {
    if (mention.value < 100) continue;
    const sentence = sentenceAround(text, mention.start, mention.end);
    const qualifier = qualifierFor(sentence);
    if (!qualifier) continue;

    const cite = sentence.match(CITE);
    return {
      amount: mention.value,
      currency: mention.currency ?? "USD",
      qualifier: qualifier.charAt(0).toUpperCase() + qualifier.slice(1),
      cite: cite ? Number(cite[1]) : null,
      at: mention.start,
    };
  }

  return null;
}

/**
 * Cuts the sentence the figure was lifted from, so the answer does not say it
 * twice.
 *
 * It is the *same* sentence the figure cites — not the first sentence that
 * happens to mention the number — so the paragraph that disappears and the
 * citation above it always agree. A sentence that also states a second price is
 * kept whole: losing the add-on prices to avoid repeating one number would be a
 * worse trade than repeating it.
 */
export function withoutPriceSentence(answer: string, price: PriceLine): string {
  const boundary = /[.!?\n]/;
  let left = Math.min(price.at, answer.length);
  while (left > 0 && !boundary.test(answer[left - 1])) left -= 1;
  let right = Math.min(price.at, answer.length);
  while (right < answer.length && !boundary.test(answer[right])) right += 1;
  if (right < answer.length) right += 1;

  const sentence = answer.slice(left, right);
  if (new Set(mentions(sentence).map((m) => m.value)).size > 1) return answer.trim();

  return (answer.slice(0, left) + answer.slice(right))
    .replace(/[ \t]{2,}/g, " ")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function formatAmount(amount: number): string {
  return amount.toLocaleString("en-US");
}
