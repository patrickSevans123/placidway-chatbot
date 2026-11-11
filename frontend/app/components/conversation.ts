import type { DonePayload, Source, Stage } from "../lib/types";

// The state one question moves through. Kept in its own module so the shell and
// the answer components agree on it without importing each other.
//
// `streaming` covers every moment before `done`; `replace` may swap the body
// during it, and `done` carries the final text.

export type TurnStatus = "streaming" | "done" | "stopped" | "error" | "limited" | "offline";

export interface Turn {
  id: number;
  question: string;
  text: string;
  stage: Stage;
  status: TurnStatus;
  done: DonePayload | null;
  /** Seconds to wait, from a 429 `Retry-After`. */
  retryAfter: number | null;
  rating: 1 | -1 | null;
  ratingFailed: boolean;
}

export interface HealthState {
  state: "loading" | "ok" | "down";
  pages: number | null;
}

export interface Live {
  stage: Stage | null;
  status: TurnStatus | null;
}

export type Sources = Source[];
