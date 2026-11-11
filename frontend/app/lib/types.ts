// Wire types for the chat API. These mirror the contract in the backend, so a
// field name here should never change without the backend changing first.

export type Stage = "retrieving" | "drafting" | "verifying";

export interface Source {
  id: string;
  title: string;
  url: string;
  page_type: string;
}

export interface DonePayload {
  session_id: string;
  answer: string;
  sources: Source[];
  language: string;
  intent: string;
  grounded: boolean;
  show_disclaimer: boolean;
  show_lead_form: boolean;
  latency_ms: number;
  model: string;
  confidence: number | null;
  prices_checked_at: string | null;
}

export interface HealthPayload {
  status?: string;
  pages?: number;
  chunks?: number;
  prices?: number;
  faqs?: number;
  model?: string;
}
