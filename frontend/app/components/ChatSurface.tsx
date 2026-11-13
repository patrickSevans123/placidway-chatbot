"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, getHealth, postFeedback } from "../lib/api";
import { ChatError, streamChat } from "../lib/stream";
import type { Stage } from "../lib/types";
import { Composer } from "./Composer";
import { Opening } from "./EmptyState";
import { Header } from "./Header";
import { TurnView } from "./Turn";
import type { HealthState, Turn } from "./conversation";

// The conversation is kept as one value, so the thread and the id the server
// continues can never be restored out of step.
const STORAGE_KEY = "placidway.chat.v1";

export default function ChatSurface() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({ state: "loading", pages: null });
  const [lit, setLit] = useState<{ turn: number; id: string } | null>(null);
  // False until the stored conversation has been read, so the first render never
  // writes an empty list over a real one.
  const [ready, setReady] = useState(false);

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(1);
  const litTimer = useRef<number | null>(null);
  const tokenBuffer = useRef("");
  const tokenFrame = useRef<number | null>(null);
  // The thread is the only scroll area. Follow the stream only while the reader
  // is already at the end of it.
  const follow = useRef(true);
  const threadRef = useRef<HTMLElement | null>(null);

  // Restore the pair, or neither. A half-restored conversation is worse than an
  // empty one: the server would answer a follow-up about a question that is not
  // on screen.
  useEffect(() => {
    let restored: { sessionId: string; turns: Turn[] } | null = null;
    try {
      const raw = sessionStorage.getItem(STORAGE_KEY);
      if (raw) {
        const data = JSON.parse(raw) as { sessionId?: unknown; turns?: unknown };
        if (typeof data?.sessionId === "string" && Array.isArray(data.turns)) {
          const saved = data.turns.filter(isTurn).map(restoreTurn);
          if (saved.length) restored = { sessionId: data.sessionId, turns: saved };
        }
      }
    } catch {
      restored = null;
    }

    if (restored) {
      setSessionId(restored.sessionId);
      setTurns(restored.turns);
      nextId.current = restored.turns.reduce((max, turn) => Math.max(max, turn.id), 0) + 1;
    } else {
      try {
        sessionStorage.removeItem(STORAGE_KEY);
      } catch {
        /* storage disabled: nothing to clear */
      }
    }
    setReady(true);
  }, []);

  // Written when the answer settles, never mid-stream: a reload must not bring
  // back half a sentence. The pair is written only when both halves exist.
  useEffect(() => {
    if (!ready) return;
    if (turns.some((turn) => turn.status === "streaming")) return;
    try {
      if (!sessionId || turns.length === 0) {
        sessionStorage.removeItem(STORAGE_KEY);
      } else {
        sessionStorage.setItem(STORAGE_KEY, JSON.stringify({ sessionId, turns }));
      }
    } catch {
      /* storage disabled: the conversation still works in memory */
    }
  }, [ready, sessionId, turns]);

  useEffect(() => {
    const control = new AbortController();
    getHealth(control.signal).then((data) =>
      setHealth({
        state: data && data.status !== "degraded" ? "ok" : "down",
        pages: typeof data?.pages === "number" ? data.pages : null,
      }),
    );
    return () => control.abort();
  }, []);

  // A reader who scrolls up to read is left where they are until they come back
  // down within 80px of the end.
  useEffect(() => {
    const el = threadRef.current;
    if (!el) return;
    const onScroll = () => {
      follow.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    };
    onScroll();
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, []);

  const scrollToEnd = useCallback(() => {
    const el = threadRef.current;
    if (!el || !follow.current) return;
    el.scrollTop = el.scrollHeight;
  }, []);

  // Follow the answer, but only from a thread the reader is already at the end
  // of. This is an effect rather than a call beside setTurns: the browser has
  // the new paragraph by the time it runs, so the scroll lands on the real
  // bottom instead of on the height of the previous render.
  useEffect(() => {
    scrollToEnd();
  }, [turns, scrollToEnd]);

  const patch = useCallback((id: number, next: Partial<Turn>) => {
    setTurns((list) => list.map((turn) => (turn.id === id ? { ...turn, ...next } : turn)));
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || busy) return;

      const id = nextId.current++;
      // Sending is a deliberate move to the end, so following resumes here even
      // if the reader had scrolled back through an earlier answer.
      follow.current = true;
      setTurns((list) => [
        ...list,
        {
          id,
          question: text,
          text: "",
          stage: "retrieving",
          status: "streaming",
          done: null,
          retryAfter: null,
          rating: null,
          ratingFailed: false,
        },
      ]);
      setBusy(true);

      const control = new AbortController();
      abortRef.current = control;
      tokenBuffer.current = "";
      let finished = false;

      const flushFrame = () => {
        if (tokenFrame.current !== null) {
          window.cancelAnimationFrame(tokenFrame.current);
          tokenFrame.current = null;
        }
        const chunk = tokenBuffer.current;
        tokenBuffer.current = "";
        return chunk;
      };

      const schedule = () => {
        if (tokenFrame.current !== null) return;
        tokenFrame.current = window.requestAnimationFrame(() => {
          tokenFrame.current = null;
          const chunk = tokenBuffer.current;
          tokenBuffer.current = "";
          if (!chunk) return;
          setTurns((list) =>
            list.map((turn) => (turn.id === id ? { ...turn, text: turn.text + chunk } : turn)),
          );
        });
      };

      try {
        await streamChat(
          API_BASE,
          { session_id: sessionId, message: text },
          {
            onStage: (stage: Stage) => patch(id, { stage }),
            onToken: (chunk) => {
              tokenBuffer.current += chunk;
              // At most one render per frame, so a fast stream cannot thrash.
              schedule();
            },
            onReplace: (answer) => {
              // `replace` carries the whole corrected answer, so the body is
              // swapped, never appended to: buffered tokens are dropped and
              // `text` is set to the new body outright.
              flushFrame();
              setTurns((list) =>
                list.map((turn) => (turn.id === id ? { ...turn, text: answer } : turn)),
              );
            },
            onDone: (done) => {
              finished = true;
              const pending = flushFrame();
              setSessionId(done.session_id);
              setTurns((list) =>
                list.map((turn) =>
                  turn.id === id
                    ? {
                        ...turn,
                        done,
                        // `done.answer` is the authoritative body; the streamed
                        // text is only a fallback if it is ever empty.
                        text: done.answer || turn.text + pending,
                        status: "done",
                      }
                    : turn,
                ),
              );
            },
          },
          control.signal,
        );
        // A stream that ends without `done` never reached the answer.
        if (!finished) patch(id, { status: "error" });
      } catch (error) {
        flushFrame();
        if (control.signal.aborted) {
          patch(id, { status: "stopped" });
        } else if (!navigator.onLine) {
          patch(id, { status: "offline" });
        } else if (error instanceof ChatError && error.status === 429) {
          patch(id, { status: "limited", retryAfter: error.retryAfter });
        } else {
          patch(id, { status: "error" });
          if (!(error instanceof ChatError)) console.warn("chat stream failed", error);
        }
      } finally {
        abortRef.current = null;
        setBusy(false);
      }
    },
    [busy, sessionId, patch],
  );

  const stop = useCallback(() => abortRef.current?.abort(), []);

  const rate = useCallback(
    async (turn: Turn, rating: 1 | -1) => {
      patch(turn.id, { rating });
      try {
        await postFeedback({ session_id: sessionId, question: turn.question, rating });
      } catch {
        patch(turn.id, { ratingFailed: true });
      }
    },
    [sessionId, patch],
  );

  // Clicking a [n] lights the page it points at, in the answer's own list. It is
  // also what unfolds that list, so the light is never scheduled into a closed
  // disclosure. Passing "" clears it.
  const cite = useCallback((turnId: number, sourceId: string) => {
    if (litTimer.current) window.clearTimeout(litTimer.current);
    if (!sourceId) {
      setLit(null);
      return;
    }
    setLit(null);
    // Two frames, so clicking the same citation twice restarts the light.
    window.requestAnimationFrame(() => {
      setLit({ turn: turnId, id: sourceId });
      litTimer.current = window.setTimeout(() => setLit(null), 2400);
    });
  }, []);

  useEffect(
    () => () => {
      if (litTimer.current) window.clearTimeout(litTimer.current);
      if (tokenFrame.current !== null) window.cancelAnimationFrame(tokenFrame.current);
      abortRef.current?.abort();
    },
    [],
  );

  const newConversation = useCallback(() => {
    abortRef.current?.abort();
    setSessionId(null);
    setTurns([]);
    setValue("");
    setLit(null);
    follow.current = true;
    threadRef.current?.scrollTo({ top: 0, behavior: "auto" });
  }, []);

  const empty = turns.length === 0;
  const opening = empty || !ready;

  return (
    <div className="shell">
      <Header onNew={empty ? undefined : newConversation} />

      <main className="thread" id="main" ref={threadRef}>
        <div className="thread-inner">
          {opening ? (
            <Opening onPick={(q) => void ask(q)} />
          ) : (
            <section className="turns" aria-label="Conversation">
              <h1 className="sr-only">
                PlacidWay treatment guide: answers about cancer treatment at ITC in Tijuana
              </h1>
              {turns.map((turn) => (
                <TurnView
                  key={turn.id}
                  turn={turn}
                  litId={lit?.turn === turn.id ? lit.id : null}
                  onCite={(sourceId) => cite(turn.id, sourceId)}
                  onRetry={() => void ask(turn.question)}
                  onRate={(rating) => void rate(turn, rating)}
                  sessionId={sessionId}
                />
              ))}
            </section>
          )}
        </div>
      </main>

      <Composer
        value={value}
        busy={busy}
        health={health}
        onChange={setValue}
        onSend={() => {
          const q = value;
          setValue("");
          void ask(q);
        }}
        onStop={stop}
        autoFocus={ready && empty}
      />

      <p className="sr-only" role="status" aria-live="polite">
        {busy ? "An answer is being written." : ""}
      </p>
    </div>
  );
}

const STATUSES = ["streaming", "done", "stopped", "error", "limited", "offline"] as const;

// A stored turn is untrusted input: anything that is not the shape the view
// expects is dropped rather than trusted into a render.
function isTurn(value: unknown): value is Partial<Turn> & { id: number; question: string } {
  if (!value || typeof value !== "object") return false;
  const turn = value as Record<string, unknown>;
  return (
    typeof turn.id === "number" &&
    Number.isFinite(turn.id) &&
    typeof turn.question === "string" &&
    typeof turn.text === "string" &&
    typeof turn.status === "string" &&
    (STATUSES as readonly string[]).includes(turn.status)
  );
}

// A turn that was still arriving when the tab was closed is shown as stopped:
// the server is not going to finish a stream nobody is listening to.
function restoreTurn(saved: Partial<Turn> & { id: number; question: string }): Turn {
  const done = saved.done ?? null;
  const status: Turn["status"] =
    saved.status === "streaming" ? "stopped" : saved.status === "done" && !done ? "error" : saved.status!;

  return {
    id: saved.id,
    question: saved.question,
    text: typeof saved.text === "string" ? saved.text : "",
    stage: saved.stage === "retrieving" || saved.stage === "drafting" || saved.stage === "verifying" ? saved.stage : "drafting",
    status,
    done,
    retryAfter: typeof saved.retryAfter === "number" ? saved.retryAfter : null,
    rating: saved.rating === 1 || saved.rating === -1 ? saved.rating : null,
    ratingFailed: saved.ratingFailed === true,
  };
}
