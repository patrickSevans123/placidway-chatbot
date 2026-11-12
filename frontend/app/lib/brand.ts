// Copy and constants shared by the shell, the opening and the contents column.
// Kept out of the components so the wording can be read and changed in one place.
//
// Everything below is taken from data/corpus.json, not written from memory: the
// seven page titles and their page types, the two programme prices, the three
// week duration, and the counts of what the index holds.

export interface PageRef {
  /** The short name used in the index. */
  title: string;
  note: string;
}

// The seven pages, in the order the corpus lists them.
export const PAGES: PageRef[] = [
  {
    title: "Clinic profile",
    note: "Doctors, facilities, accreditations",
  },
  {
    title: "Adenocarcinoma package",
    note: "The two prices, inclusions, recovery",
  },
  {
    title: "Adrenal cancer package",
    note: "Price, inclusions, recovery",
  },
  {
    title: "Anal cancer package",
    note: "Price, inclusions, recovery",
  },
  {
    title: "Clinic videos",
    note: "Patient testimonials and explainers",
  },
  {
    title: "Price list",
    note: "Every procedure, priced separately",
  },
  {
    title: "Price comparison",
    note: "Alternative medicine by country",
  },
];

/** What the index actually holds. Counted from the corpus, not estimated. */
export const CORPUS = {
  pages: 7,
  passages: 183,
  prices: 69,
  answers: 19,
};

/** How many pages the answers are drawn from. Shown in the header and the trust line. */
export const PAGE_COUNT = CORPUS.pages;

/** The date the price list was last confirmed, in one place so nothing drifts. */
export const PRICES_CHECKED = "11 Nov 2026";

export interface Tier {
  label: string;
  /** Already formatted the way the package page prints it. */
  amount: string;
}

// The package pages print a two-row table: programme, duration, total. These are
// those two rows. The figure is the corpus's own; nothing here is rounded.
export const TIERS: Tier[] = [
  { label: "Out-patient", amount: "18,995" },
  { label: "In-patient", amount: "30,000" },
];

export interface Prompt {
  question: string;
  note: string;
}

// Every question below is answered by one of the seven indexed pages.
export const PROMPTS: Prompt[] = [
  {
    question: "How much does adenocarcinoma treatment cost?",
    note: "The package price, and what the add-ons cost",
  },
  {
    question: "What does the in-patient programme include?",
    note: "What the higher tier adds",
  },
  {
    question: "Who are the doctors at ITC?",
    note: "The medical team named on the clinic page",
  },
];

export const STAGE_TEXT = {
  retrieving: "Finding the pages that answer this",
  drafting: "Writing the answer",
} as const;

/** The two stages a reader can actually see. `verifying` takes milliseconds on
 *  the server and is reported in the finished answer instead. */
export type VisibleStage = keyof typeof STAGE_TEXT;

export const QUOTE_URL =
  "https://www.placidway.com/rfi/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center";
