import type { DonePayload, Stage } from "./types";

// Server-sent events are parsed by hand because EventSource cannot POST.
// A block is separated by a blank line; several `data:` lines in one block are
// joined with a newline, as the format specifies.

export interface StreamHandlers {
  onStage: (stage: Stage) => void;
  onToken: (text: string) => void;
  onReplace: (answer: string) => void;
  onDone: (done: DonePayload) => void;
}

export class ChatError extends Error {
  constructor(
    message: string,
    readonly status?: number,
    /** Seconds to wait, from a 429 `Retry-After`. */
    readonly retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ChatError";
  }
}

export async function streamChat(
  baseUrl: string,
  body: { session_id: string | null; message: string },
  handlers: StreamHandlers,
  signal: AbortSignal,
): Promise<void> {
  const response = await fetch(`${baseUrl}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
    body: JSON.stringify(body),
    signal,
  });

  if (!response.ok || !response.body) {
    throw new ChatError("The answer service did not respond.", response.status, retryAfterOf(response));
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  const handleBlock = (block: string) => {
    let event = "message";
    const data: string[] = [];
    for (const line of block.split("\n")) {
      if (!line || line.startsWith(":")) continue;
      if (line.startsWith("event:")) event = line.slice(6).trim();
      else if (line.startsWith("data:")) data.push(line.slice(5).replace(/^ /, ""));
    }
    if (!data.length) return;

    let payload: unknown;
    try {
      payload = JSON.parse(data.join("\n"));
    } catch {
      return;
    }
    // `partial` events carry the whole answer so far. The streamed tokens are
    // already on screen and the final text comes from `replace` or `done`, so
    // these are skipped rather than guessed at.
    if (event === "stage") handlers.onStage((payload as { stage: Stage }).stage);
    else if (event === "token") handlers.onToken((payload as { text: string }).text ?? "");
    else if (event === "replace") handlers.onReplace((payload as { answer: string }).answer ?? "");
    else if (event === "done") handlers.onDone(payload as DonePayload);
  };

  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let split: number;
    while ((split = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, split).replace(/\r/g, "");
      buffer = buffer.slice(split + 2);
      handleBlock(block);
    }
  }
  const tail = (buffer + decoder.decode()).replace(/\r/g, "").trim();
  if (tail) handleBlock(tail);
}

function retryAfterOf(response: Response): number | null {
  const raw = response.headers.get("Retry-After");
  if (!raw) return null;
  const seconds = Number(raw);
  return Number.isFinite(seconds) && seconds > 0 ? seconds : null;
}
