import { API_BASE } from "./api";

// The free-quote form writes a lead to the backend, which is what gives a
// coordinator something to reply to. A failure is reported to the reader rather
// than swallowed, because they have just typed their email expecting a reply.

export interface LeadBody {
  session_id: string | null;
  name: string;
  email: string;
  message: string | null;
}

export type LeadResult = { ok: true } | { ok: false; problem: "email" | "network" };

export async function postLead(body: LeadBody): Promise<LeadResult> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/api/lead`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify(body),
    });
  } catch {
    return { ok: false, problem: "network" };
  }

  // 422 means the address did not pass the server's check.
  if (response.status === 422) return { ok: false, problem: "email" };
  if (!response.ok) return { ok: false, problem: "network" };
  return { ok: true };
}
