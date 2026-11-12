"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { API_BASE, getHealth, postFeedback } from "../lib/api";
import { PAGE_COUNT, PRICES_CHECKED } from "../lib/brand";
import { ChatError, streamChat } from "../lib/stream";
import type { Stage } from "../lib/types";
import { Composer } from "./Composer";
import { Contents } from "./Contents";
import { EmptyState } from "./EmptyState";
import { Header } from "./Header";
import { TurnView } from "./Turn";
import type { HealthState, Turn } from "./conversation";

const SESSION_KEY = "placidway.session_id";

export default function ChatSurface() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({ state: "loading", pages: null });
  const [lit, setLit] = useState<string | null>(null);
  const [dockHeight, setDockHeight] = useState(0);

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(1);
  const litTimer = useRef<number | null>(null);
  const tokenBuffer = useRef("");
  const tokenFrame = useRef<number | null>(null);
  // Only follow the stream when the reader is already at the bottom. Set by the
  // scroll listener, read by the token flush.
  const follow = useRef(true);

  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) setSessionId(saved);
    } catch {
      /* storage disabled: the conversation still works in memory */
    }
  }, []);

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
  // down within 80px of the bottom.
  useEffect(() => {
    const onScroll = () => {
      const at = window.innerHeight + window.scrollY;
      follow.current = at >= document.documentElement.scrollHeight - 80;
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const saveSession = useCallback((id: string | null) => {
    setSessionId(id);
    try {
      if (id) sessionStorage.setItem(SESSION_KEY, id);
      else sessionStorage.removeItem(SESSION_KEY);
    } catch {
      /* ignore */
    }
  }, []);

  const patch = useCallback((id: number, next: Partial<Turn>) => {
    setTurns((list) => list.map((turn) => (turn.id === id ? { ...turn, ...next } : turn)));
  }, []);

  const scrollToEnd = useCallback(() => {
    if (!follow.current) return;
    window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "auto" });
  }, []);

  const ask = useCallback(
    async (question: string) => {
      const text = question.trim();
      if (!text || busy) return;

      const id = nextId.current++;
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
      // Asking is a deliberate move to the end, so following resumes here.
      follow.current = true;

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
          scrollToEnd();
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
              scrollToEnd();
            },
            onDone: (done) => {
              finished = true;
              const pending = flushFrame();
              saveSession(done.session_id);
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
              scrollToEnd();
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
    [busy, sessionId, patch, saveSession, scrollToEnd],
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

  // Clicking a [n] scrolls the source card into view and lights it. Passing ""
  // clears a lit card, which the card calls when its own pulse ends.
  const cite = useCallback((sourceId: string) => {
    if (litTimer.current) window.clearTimeout(litTimer.current);
    if (!sourceId) {
      setLit(null);
      return;
    }
    setLit(null);
    // Two frames, so clicking the same citation twice restarts the pulse.
    window.requestAnimationFrame(() => {
      setLit(sourceId);
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

  const newQuestion = useCallback(() => {
    abortRef.current?.abort();
    saveSession(null);
    setTurns([]);
    setValue("");
    setLit(null);
    follow.current = true;
    window.scrollTo({ top: 0, behavior: "auto" });
  }, [saveSession]);

  const empty = turns.length === 0;

  return (
    <div className="app" style={{ paddingBottom: dockHeight, "--dock": `${dockHeight}px` } as React.CSSProperties}>
      <Header onNew={newQuestion} showNew={!empty} />

      <main className="page" id="main">
        <h1 className="sr-only">PlacidWay treatment guide: cancer treatment at ITC in Tijuana</h1>

        <div className={`layout${empty ? " layout-index" : ""}`}>
          <div className="column">
            {empty ? (
              <section className="intro" aria-labelledby="empty-title">
                <p className="eyebrow">
                  <span className="eyebrow-tick" aria-hidden="true" />
                  ITC Immunity Therapy Center · Tijuana, Mexico
                </p>
                <h2 className="intro-title" id="empty-title">
                  What cancer treatment at ITC costs.
                </h2>
                <p className="intro-lede">
                  Ask about a price, a programme, the doctors or the trip. Answers are written only
                  from the seven PlacidWay pages each one cites.
                </p>
                <EmptyState onPick={(q) => void ask(q)} />
              </section>
            ) : (
              <section aria-label="Answers" className="turns">
                <h2 className="sr-only">Answers</h2>
                {turns.map((turn) => (
                  <TurnView
                    key={turn.id}
                    turn={turn}
                    lit={lit}
                    onCite={cite}
                    onRetry={() => void ask(turn.question)}
                    onRate={(rating) => void rate(turn, rating)}
                    sessionId={sessionId}
                  />
                ))}
              </section>
            )}

            <TrustLine health={health} />
          </div>

          {empty && <Contents />}
        </div>

        <Footer health={health} />
      </main>

      <Composer
        value={value}
        busy={busy}
        onChange={setValue}
        onSend={() => {
          const q = value;
          setValue("");
          void ask(q);
        }}
        onStop={stop}
        onHeight={setDockHeight}
      />

      <p className="sr-only" role="status" aria-live="polite">
        {busy ? "An answer is being written." : ""}
      </p>
    </div>
  );
}

// Where their accreditations row sits: the honest version of a trust cue.
// One line, not a strip of four figures, so it reads as a caption rather than a
// second page furniture.
function TrustLine({ health }: { health: HealthState }) {
  return (
    <section className="trust" aria-label="About these answers">
      <p className="trust-line">
        <span>Answers come only from these {PAGE_COUNT} PlacidWay pages</span>
        <span>
          Prices checked <span className="tabular">{PRICES_CHECKED}</span>
        </span>
      </p>
    </section>
  );
}

function Footer({ health }: { health: HealthState }) {
  const line =
    health.state === "loading"
      ? "Checking the answer service…"
      : health.state === "down"
        ? "The answer service is not responding right now."
        : "Answer service ready";

  return (
    <footer className="foot">
      <p className="foot-line">
        <span className={`status-dot${health.state === "ok" ? " status-ok" : ""}`} aria-hidden="true" />
        <span className="foot-status">{line}</span>
      </p>
    </footer>
  );
}
