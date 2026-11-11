// Copy and constants shared by the shell and the empty state. Kept out of the
// components so the wording can be read and changed in one place.

export interface Starter {
  question: string;
  note: string;
  icon: "price" | "list" | "doctor" | "route" | "review" | "video";
}

// Every question below is answered by one of the seven indexed pages.
export const STARTERS: Starter[] = [
  {
    question: "How much does adenocarcinoma treatment cost?",
    note: "The package price, and what add-ons cost",
    icon: "price",
  },
  {
    question: "What does the in-patient programme include?",
    note: "The higher price tier, and what it adds",
    icon: "list",
  },
  {
    question: "Who are the doctors at ITC?",
    note: "The medical team named on the clinic page",
    icon: "doctor",
  },
  {
    question: "What is included in the adrenal cancer package?",
    note: "What one treatment programme covers",
    icon: "route",
  },
  {
    question: "What do patients say about the clinic?",
    note: "Reviews quoted on the clinic page",
    icon: "review",
  },
  {
    question: "Where can I see the clinic before I travel?",
    note: "Videos from the clinic",
    icon: "video",
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

/** How many pages the answers are drawn from. Shown in the header and the trust line. */
export const PAGE_COUNT = 7;
