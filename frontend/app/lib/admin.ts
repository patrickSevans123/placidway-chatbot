import { API_BASE } from "./api";

// The operator console is the only place in the app that holds a credential.
// It lives in sessionStorage for the tab's lifetime and is sent as a header, so
// it never reaches the exported bundle, a URL, or a console line.
export const ADMIN_TOKEN_KEY = "placidway.admin.token";

export class AdminRequestError extends Error {
  readonly status: number;
  readonly detail: string | null;

  constructor(status: number, detail: string | null) {
    super(detail ?? `admin request failed (${status})`);
    this.name = "AdminRequestError";
    this.status = status;
    this.detail = detail;
  }
}

export function isTokenRejected(error: unknown): boolean {
  // The backend answers 401; 403 is accepted too because a proxy in front of it
  // may normalise the two. Both mean the same thing to the operator.
  return (
    error instanceof AdminRequestError && (error.status === 401 || error.status === 403)
  );
}

export function isAdminDisabled(error: unknown): boolean {
  // 503 from /api/admin/* also covers a refresh rejected by the sanity gate, so
  // the detail has to be read before assuming the server is unconfigured.
  return (
    error instanceof AdminRequestError &&
    error.status === 503 &&
    !(error.detail ?? "").startsWith("refresh rejected")
  );
}

async function readDetail(response: Response): Promise<string | null> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail?: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  } catch {
    // A body that is not JSON carries no detail worth showing.
  }
  return null;
}

async function request<T>(path: string, token?: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...init,
      headers: {
        Accept: "application/json",
        ...(token ? { "X-Admin-Token": token } : {}),
        ...init?.headers,
      },
      cache: "no-store",
    });
  } catch {
    throw new AdminRequestError(0, "The API did not answer. Is the backend running?");
  }
  if (!response.ok) {
    throw new AdminRequestError(response.status, await readDetail(response));
  }
  return (await response.json()) as T;
}

export interface AdminStats {
  sessions: number;
  messages: number;
  unanswered: number;
  leads: number;
  feedback_up: number;
  feedback_down: number;
}

export interface UnansweredRow {
  question: string;
  intent: string | null;
  confidence: number | null;
  created_at: string | null;
}

export interface UnansweredPayload {
  unanswered: UnansweredRow[];
}

export interface CorpusDiff {
  prices_added: number;
  prices_removed: number;
  prices_moved: string[];
  chunks_added: number;
  chunks_removed: number;
}

export interface RefreshStatus {
  last_checked: string | null;
  last_changed: string | null;
  last_result: string | null;
  last_reason: string | null;
  changed_pages: string[];
  corpus_built_at: string | null;
  last_diff: CorpusDiff | null;
}

export interface RefreshOutcome {
  ok: boolean;
  changed: boolean;
  reason: string | null;
  pages: number;
  chunks: number;
  prices: number;
  changed_pages: string[];
  seconds: number;
  checked_at: string;
  built_at: string | null;
  diff: CorpusDiff | null;
}

// /api/health is public, so the console reads it without a token. Only the
// editor's own fields are typed here; the backend may add more.
export interface AdminHealth {
  status?: string;
  pages?: number;
  chunks?: number;
  prices?: number;
  faqs?: number;
  model?: string;
  last_ingest?: string | null;
  refresh?: RefreshStatus;
  stats?: AdminStats;
}

export function getAdminHealth(): Promise<AdminHealth> {
  return request<AdminHealth>("/api/health");
}

export function getAdminStats(token: string): Promise<AdminStats> {
  return request<AdminStats>("/api/admin/stats", token);
}

export function getUnanswered(token: string): Promise<UnansweredPayload> {
  return request<UnansweredPayload>("/api/admin/unanswered", token);
}

export function getRefreshStatus(token: string): Promise<RefreshStatus> {
  return request<RefreshStatus>("/api/admin/refresh/status", token);
}

export function postRefresh(token: string, force = false): Promise<RefreshOutcome> {
  return request<RefreshOutcome>(
    `/api/admin/refresh${force ? "?force=1" : ""}`,
    token,
    { method: "POST" },
  );
}
