import type { HealthPayload } from "./types";

// Same-origin in production, where FastAPI serves the exported folder and the
// API together. `next dev` talks to the backend on :8099 through the CORS
// headers it sets for localhost:3000.
export const API_BASE = (process.env.NEXT_PUBLIC_API_BASE ?? "").replace(/\/$/, "");

export async function postFeedback(body: {
  session_id: string | null;
  question: string;
  rating: 1 | -1;
}): Promise<void> {
  const response = await fetch(`${API_BASE}/api/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  // The rating is a side channel. A failed save is silent by design.
  if (!response.ok) throw new Error(`feedback ${response.status}`);
}

export async function getHealth(signal?: AbortSignal): Promise<HealthPayload | null> {
  try {
    const response = await fetch(`${API_BASE}/api/health`, {
      headers: { Accept: "application/json" },
      signal,
    });
    if (!response.ok) return null;
    return (await response.json()) as HealthPayload;
  } catch {
    return null;
  }
}
