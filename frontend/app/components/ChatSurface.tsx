"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { API_BASE, getHealth, postFeedback } from "../lib/api";
import { parseBlocks, parseInline, readableUrl, type Inline } from "../lib/markdown";
import { extractPrice, formatAmount, withoutPriceSentence, type PriceLine } from "../lib/price";
import { ChatError, streamChat } from "../lib/stream";
import type { DonePayload, HealthPayload, Source, Stage } from "../lib/types";

// ---------------------------------------------------------------------------
// Static copy. Questions are ones the seven pages actually answer: both price
// tiers, the doctors, and the trip.
// ---------------------------------------------------------------------------

const STARTERS = [
  { q: "How much does adenocarcinoma treatment cost?", note: "both programme prices" },
  { q: "What does the in-patient programme include?", note: "rooms, meals, supervision" },
  { q: "Who are the doctors at ITC?", note: "the medical team" },
  { q: "What is included in the adrenal cancer package?", note: "what a programme covers" },
];

const STAGE_TEXT: Record<Stage, string> = {
  retrieving: "Searching the seven pages",
  drafting: "Writing",
  verifying: "Checking the answer",
};

const QUOTE_URL =
  "https://www.placidway.com/rfi/5/Alternative-Cancer-Treatment-by-ITC-Immunity-Therapy-Center";

const SESSION_KEY = "placidway.session_id";

type TurnStatus = "streaming" | "done" | "stopped" | "error";

interface Turn {
  id: number;
  question: string;
  text: string;
  stage: Stage;
  status: TurnStatus;
  done: DonePayload | null;
  /** The figure lifted out of the answer, once `done` has arrived. */
  price: PriceLine | null;
  rating: 1 | -1 | null;
  ratingFailed: boolean;
}

interface HealthState {
  state: "loading" | "ok" | "down";
  data: HealthPayload | null;
}

// ---------------------------------------------------------------------------
// Shell
// ---------------------------------------------------------------------------

export default function ChatSurface() {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [health, setHealth] = useState<HealthState>({ state: "loading", data: null });
  const [resumed, setResumed] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);

  const abortRef = useRef<AbortController | null>(null);
  const nextId = useRef(1);
  const pendingScroll = useRef(false);
  const flashTimer = useRef<number | null>(null);
  const tokenBuffer = useRef("");
  const tokenFrame = useRef<number | null>(null);

  // Session id survives a reload so the backend keeps the conversation; the
  // transcript does not, so the first new question says so.
  useEffect(() => {
    try {
      const saved = sessionStorage.getItem(SESSION_KEY);
      if (saved) {
        setSessionId(saved);
        setResumed(true);
      }
    } catch {
      /* storage disabled: the conversation still works in memory */
    }
  }, []);

  useEffect(() => {
    const control = new AbortController();
    getHealth(control.signal).then((data) =>
      setHealth({ state: data ? "ok" : "down", data }),
    );
    return () => control.abort();
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
    setTurns((list) => list.map((t) => (t.id === id ? { ...t, ...next } : t)));
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
          price: null,
          rating: null,
          ratingFailed: false,
        },
      ]);
      setBusy(true);
      pendingScroll.current = true;

      const control = new AbortController();
      abortRef.current = control;
      tokenBuffer.current = "";
      let finished = false;

      const startFrame = () => {
        if (tokenFrame.current !== null) return;
        tokenFrame.current = window.requestAnimationFrame(() => {
          tokenFrame.current = null;
          const chunk = tokenBuffer.current;
          tokenBuffer.current = "";
          if (!chunk) return;
          pendingScroll.current = true;
          setTurns((list) =>
            list.map((t) => (t.id === id ? { ...t, text: t.text + chunk } : t)),
          );
        });
      };

      const flushFrame = () => {
        if (tokenFrame.current !== null) {
          window.cancelAnimationFrame(tokenFrame.current);
          tokenFrame.current = null;
        }
        const chunk = tokenBuffer.current;
        tokenBuffer.current = "";
        return chunk;
      };

      try {
        await streamChat(
          API_BASE,
          { session_id: sessionId, message: text },
          {
            onStage: (stage) => patch(id, { stage }),
            onToken: (chunk) => {
              tokenBuffer.current += chunk;
              // At most one render per frame, however fast the tokens come.
              startFrame();
            },
            onReplace: (answer) => {
              // `replace` carries the whole corrected answer. Drop any buffered
              // tokens first, so the body is swapped rather than appended to.
              flushFrame();
              pendingScroll.current = true;
              setTurns((list) =>
                list.map((t) => (t.id === id ? { ...t, text: answer } : t)),
              );
            },
            onDone: (done) => {
              finished = true;
              const pendingText = flushFrame();
              pendingScroll.current = true;
              saveSession(done.session_id);
              const sources = Array.isArray(done.sources) ? done.sources : [];
              const price = done.grounded ? extractPrice(done.answer) : null;
              setTurns((list) =>
                list.map((t) =>
                  t.id === id
                    ? {
                        ...t,
                        done,
                        sources,
                        price,
                        text: done.answer || t.text + pendingText,
                        status: "done",
                      }
                    : t,
                ),
              );
            },
          },
          control.signal,
        );
        if (!finished) patch(id, { status: "error" });
      } catch (error) {
        flushFrame();
        if (control.signal.aborted) {
          patch(id, { status: "stopped" });
        } else {
          patch(id, { status: "error" });
          if (!(error instanceof ChatError)) console.warn("chat stream failed", error);
        }
      } finally {
        abortRef.current = null;
        setBusy(false);
      }
    },
    [busy, sessionId, patch, saveSession],
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

  const flashSource = useCallback((id: string) => {
    if (flashTimer.current) window.clearTimeout(flashTimer.current);
    setFlash(id);
    flashTimer.current = window.setTimeout(() => setFlash(null), 1800);
  }, []);

  useEffect(
    () => () => {
      if (flashTimer.current) window.clearTimeout(flashTimer.current);
      abortRef.current?.abort();
    },
    [],
  );

  const empty = turns.length === 0;

  return (
    <>
      <Header onNew={() => {
        abortRef.current?.abort();
        saveSession(null);
        setTurns([]);
        setResumed(false);
        setValue("");
      }} showNew={!empty || resumed} />

      <main className="sheet">
        <section className="intro" aria-labelledby="title">
          <p className="scroll-no" aria-hidden="true">
            <span className="scroll-no-long">Seven pages · answers with the page they came from</span>
            <span className="scroll-no-short">Seven pages</span>
          </p>
          <h1 id="title">Cancer treatment in Tijuana, read from the pages.</h1>
          <p className="lede">
            Ask about prices, what a programme includes, the doctors or the trip. Every answer
            comes from seven PlacidWay source pages, and shows the page it came from.
          </p>
        </section>

        {resumed && empty && (
          <p className="resume">
            Your earlier questions are not shown after a page reload, but the guide still
            remembers the conversation. Carry on with a follow-up.
          </p>
        )}

        <div className="record">
          <section className="record-main" aria-label="Conversation">
            <h2 className="sr-only">Conversation</h2>

            {empty ? (
              <EmptyState onPick={(q) => ask(q)} />
            ) : (
              <ol className="turns">
                {turns.map((turn) => (
                  <li key={turn.id} className="turn">
                    <TurnRow
                      turn={turn}
                      flash={flash}
                      onRate={(r) => rate(turn, r)}
                      onFlash={flashSource}
                      onRetry={() => ask(turn.question)}
                    />
                  </li>
                ))}
              </ol>
            )}
            <Live stage={turns.length > 0 ? turns[turns.length - 1].stage : null} status={turns.length > 0 ? turns[turns.length - 1].status : null} />
          </section>

          <aside className="rail" aria-label="About this guide">
            <Contents />
            <div className="rail-block">
              <p className="rail-label">The pages</p>
              <p className="rail-text">
                The guide answers from seven pages only. If a question is not covered there, it
                says so and offers a free quote instead of guessing.
              </p>
            </div>
            <Disclaimer />
          </aside>
        </div>

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
        />
      </main>

      <Footer health={health} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

function Header({ onNew, showNew }: { onNew: () => void; showNew: boolean }) {
  return (
    <header className="top">
      <div className="top-inner">
        <a className="brand" href="./" aria-label="PlacidWay guide, start a new conversation">
          <BrandMark />
          <span className="brand-name">PlacidWay</span>
          <span className="brand-sep" aria-hidden="true" />
          <span className="brand-sub">Treatment guide</span>
        </a>
        <nav className="top-actions" aria-label="Site">
          {showNew && (
            <button type="button" className="linkish" onClick={onNew}>
              Start again
            </button>
          )}
          <a
            className="linkish"
            href="https://www.placidway.com/"
            target="_blank"
            rel="noopener"
          >
            PlacidWay.com
            <span className="sr-only"> (opens in a new tab)</span>
            <Arrow className="tiny" />
          </a>
        </nav>
      </div>
    </header>
  );
}

function BrandMark() {
  // A plus inside a record seal: the clinic mark of the old page, redrawn as a
  // stamped rule rather than a soft app icon.
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="10.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
      <path d="M12 6.6v10.8M6.6 12h10.8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Empty state
// ---------------------------------------------------------------------------

function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="empty">
      <h2 className="empty-title">Start with a question</h2>
      <p className="empty-sub">
        These are the ones people ask most. Or type your own below.
      </p>
      <ol className="starters">
        {STARTERS.map((s, i) => (
          <li key={s.q}>
            <button type="button" className="starter" onClick={() => onPick(s.q)}>
              <span className="starter-num" aria-hidden="true">
                {String(i + 1).padStart(2, "0")}
              </span>
              <span className="starter-body">
                <span className="starter-q">{s.q}</span>
                <span className="starter-note">{s.note}</span>
              </span>
              <Arrow className="starter-arrow" />
            </button>
          </li>
        ))}
      </ol>
    </div>
  );
}

// ---------------------------------------------------------------------------
// A question and its answer
// ---------------------------------------------------------------------------

function TurnRow({
  turn,
  flash,
  onRate,
  onFlash,
  onRetry,
}: {
  turn: Turn;
  flash: string | null;
  onRate: (r: 1 | -1) => void;
  onFlash: (id: string) => void;
  onRetry: () => void;
}) {
  const done = turn.done;

  return (
    <>
      <div className="turn-q">
        <span className="turn-q-label">You asked</span>
        <p className="turn-q-text">{turn.question}</p>
      </div>

      <div className="turn-a">
        {turn.status === "streaming" && (
          <>
            <p className="stage" aria-hidden="true">
              {STAGE_TEXT[turn.stage]}
            </p>
            <AnswerBare text={turn.text} streaming />
          </>
        )}

        {turn.status === "stopped" && (
          <div className="notice">
            <p className="notice-text">Stopped. This answer was not kept.</p>
            <button type="button" className="linkish" onClick={onRetry}>
              Ask it again
            </button>
          </div>
        )}

        {turn.status === "error" && (
          <div className="notice">
            <p className="notice-text">
              The guide could not reach its pages. Check your connection, then try once more.
            </p>
            <button type="button" className="linkish" onClick={onRetry}>
              Try again
            </button>
          </div>
        )}

        {turn.status === "done" && done && (
          <Answered turn={turn} done={done} flash={flash} onRate={onRate} onFlash={onFlash} onRetry={onRetry} />
        )}
      </div>
    </>
  );
}

function Answered({
  turn,
  done,
  flash,
  onRate,
  onFlash,
  onRetry,
}: {
  turn: Turn;
  done: DonePayload;
  flash: string | null;
  onRate: (r: 1 | -1) => void;
  onFlash: (id: string) => void;
  onRetry: () => void;
}) {
  // Two markers can be on screen, never both: whatever the figure cited, and
  // whatever citation was clicked last.
  const [figureOpen, setFigureOpen] = useState(true);

  if (!done.grounded) {
    return <Refusal answer={done.answer} />;
  }

  const price = extractPrice(done.answer);
  const prose = price ? withoutPriceSentence(done.answer, price) : done.answer;
  const shown = price && figureOpen ? prose : done.answer;
  const priceSource = price?.cite ? (done.sources[price.cite - 1] ?? null) : null;

  // Every marker that has a card is a link to that card.
  return (
    <>
      {price && (
        <PriceBlock
          price={price}
          source={priceSource}
          onFlash={onFlash}
          onToggle={() => setFigureOpen((open) => !open)}
          bodyOpen={figureOpen}
          hasProse={prose.trim().length > 0}
        />
      )}
      {shown.trim() && (
        <AnswerMarkdown
          markdown={shown}
          sources={done.sources}
          onFlash={onFlash}
          linked={done.sources.length}
        />
      )}
      <Body done={done} />
      <Feedback turn={turn} onRate={onRate} />
      <Sources sources={done.sources} flash={flash} onFlash={onFlash} />
      <CheckedAt value={done.prices_checked_at} />
    </>
  );
}

// ---------------------------------------------------------------------------
// Price: the primary object of a price answer
// ---------------------------------------------------------------------------

function PriceBlock({
  price,
  source,
  onFlash,
  onToggle,
  bodyOpen,
  hasProse,
}: {
  price: PriceLine;
  source: Source | null;
  onFlash: (id: string) => void;
  onToggle: () => void;
  bodyOpen: boolean;
  hasProse: boolean;
}) {
  return (
    <div className="price">
      <p className="price-cap">
        <span className="price-cap-word">{price.qualifier}</span>
        {source && (
          <CiteLink
            n={price.cite ?? 1}
            id={source.id}
            label={`Source ${price.cite ?? 1}: ${source.title}`}
            onFlash={onFlash}
          />
        )}
      </p>
      <p className="price-figure">
        <span className="price-currency">{price.currency}</span>
        <span className="price-amount tabular">{formatAmount(price.amount)}</span>
      </p>
      {hasProse && (
        <button
          type="button"
          className="price-toggle"
          onClick={onToggle}
          aria-expanded={bodyOpen}
        >
          {bodyOpen ? "Hide the written answer" : "Show the written answer"}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Prose
// ---------------------------------------------------------------------------

// While tokens arrive the text is plain, with newlines kept. Partial markdown
// re-lays itself out on nearly every chunk, so it is only parsed at `done`.
function AnswerBare({ text, streaming }: { text: string; streaming?: boolean }) {
  return (
    <div className="prose prose-stream" aria-hidden={streaming ? "true" : undefined}>
      {text.trim() ? text : <span className="placeholder">Reading the pages…</span>}
      {streaming && <span className="caret" aria-hidden="true" />}
    </div>
  );
}

// Parses the finished answer once: paragraphs, lists, bold, citations.
// `linked` is how many leading sources have a card above the list, so a marker
// outside that range is drawn as a quiet number instead of a dead link.
function AnswerMarkdown({
  markdown,
  sources,
  onFlash,
  linked,
}: {
  markdown: string;
  sources: Source[];
  onFlash: (id: string) => void;
  linked: number;
}) {
  const blocks = useMemo(() => parseBlocks(markdown), [markdown]);
  return (
    <div className="prose">
      {blocks.map((block, i) => {
        if (block.kind === "p") {
          return (
            <p key={i}>
              <InlineText parts={parseInline(block.text, sources.length)} sources={sources} linked={linked} onFlash={onFlash} />
            </p>
          );
        }
        const Tag = block.kind;
        return (
          <Tag key={i} className={block.kind === "ol" ? "steps" : undefined}>
            {block.items.map((item, j) => (
              <li key={j}>
                <InlineText parts={parseInline(item, sources.length)} sources={sources} linked={linked} onFlash={onFlash} />
              </li>
            ))}
          </Tag>
        );
      })}
    </div>
  );
}

function InlineText({
  parts,
  sources,
  linked,
  onFlash,
}: {
  parts: Inline[];
  sources: Source[];
  linked: number;
  onFlash: (id: string) => void;
}) {
  return (
    <>
      {parts.map((part, i) => {
        if (part.kind === "bold") return <strong key={i}>{part.text}</strong>;
        if (part.kind === "cite") {
          const source = sources[part.n - 1];
          if (part.n > linked || !source) {
            return (
              <span key={i} className="cite cite-quiet" aria-label={`See source ${part.n} below`}>
                {part.n}
              </span>
            );
          }
          return (
            <CiteLink
              key={i}
              n={part.n}
              id={source.id}
              label={`Source ${part.n}: ${source.title}`}
              onFlash={onFlash}
            />
          );
        }
        return <span key={i}>{part.text}</span>;
      })}
    </>
  );
}

function CiteLink({
  n,
  id,
  label,
  onFlash,
  children,
}: {
  n: number;
  id: string;
  label: string;
  onFlash: (id: string) => void;
  children?: React.ReactNode;
}) {
  return (
    <a
      className="cite"
      href={`#source-${id}`}
      aria-label={label}
      onClick={(event) => {
        event.preventDefault();
        onFlash(id);
      }}
    >
      {children ?? n}
    </a>
  );
}

// ---------------------------------------------------------------------------
// Under the answer: the small truthful facts, then the rating
// ---------------------------------------------------------------------------

function Body({ done }: { done: DonePayload }) {
  const seconds = (done.latency_ms / 1000).toFixed(1);
  return (
    <p className="byline">
      <span>
        From <span className="tabular">{done.sources.length}</span>{" "}
        {done.sources.length === 1 ? "page" : "pages"} of this guide
      </span>
      <span className="byline-sep" aria-hidden="true" />
      <span>
        Answered in <span className="tabular">{seconds}</span> s
      </span>
      <span className="byline-sep" aria-hidden="true" />
      <span>{languageName(done.language)}</span>
    </p>
  );
}

function languageName(code: string): string {
  const map: Record<string, string> = {
    en: "English", es: "Español", fr: "Français", de: "Deutsch", pt: "Português",
    it: "Italiano", nl: "Nederlands", ar: "العربية", ru: "Русский", tr: "Türkçe",
    zh: "中文", ja: "日本語", ko: "한국어", hi: "हिन्दी", pl: "Polski", sv: "Svenska",
  };
  return map[code.slice(0, 2).toLowerCase()] ?? code.toUpperCase();
}

function Feedback({ turn, onRate }: { turn: Turn; onRate: (r: 1 | -1) => void }) {
  const rated = turn.rating !== null;
  return (
    <div className="feedback">
      <span className="feedback-q" id={`fb-${turn.id}`}>
        Was this useful?
      </span>
      <button
        type="button"
        className="rate"
        aria-label="This answer was useful"
        aria-describedby={`fb-${turn.id}`}
        aria-pressed={turn.rating === 1}
        disabled={rated}
        onClick={() => onRate(1)}
      >
        <Thumb up />
      </button>
      <button
        type="button"
        className="rate"
        aria-label="This answer was not useful"
        aria-describedby={`fb-${turn.id}`}
        aria-pressed={turn.rating === -1}
        disabled={rated}
        onClick={() => onRate(-1)}
      >
        <Thumb />
      </button>
      <span className="feedback-note" role="status">
        {rated
          ? turn.ratingFailed
            ? "Thanks. We could not save it just now."
            : "Thanks, noted."
          : ""}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Sources
// ---------------------------------------------------------------------------

function Sources({
  sources,
  flash,
  onFlash,
}: {
  sources: Source[];
  flash: string | null;
  onFlash: (id: string) => void;
}) {
  if (!sources.length) return null;
  return (
    <section className="sources" aria-label="Pages this answer came from">
      <ul className="source-list">
        {sources.map((source, i) => {
          const lit = flash === source.id;
          return (
            <li
              key={source.id}
              id={`source-${source.id}`}
              ref={(node) => {
                // A citation click lights the card and brings it into view. The
                // animation is CSS; reduced motion keeps the tint only.
                if (!lit || !node || node.dataset.shown === "1") return;
                node.dataset.shown = "1";
                node.scrollIntoView({
                  block: "nearest",
                  behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
                    ? "auto"
                    : "smooth",
                });
              }}
              className={`source${i === 0 ? " source-first" : ""}${lit ? " is-flash" : ""}`}
              aria-current={lit ? "true" : undefined}
            >
              <span className="source-num tabular" aria-hidden="true">
                {i + 1}
              </span>
            <span className="source-body">
              <a className="source-title" href={source.url} target="_blank" rel="noopener">
                {source.title}
                <Arrow className="inline-arrow" />
                <span className="sr-only"> (opens in a new tab)</span>
              </a>
              <span className="source-meta">
                <span className="badge">{source.page_type}</span>
                <span className="source-url">{readableUrl(source.url)}</span>
              </span>
            </span>
            </li>
          );
        })}
      </ul>
    </section>
  );
}

function CheckedAt({ value }: { value: string | null }) {
  if (!value) return null;
  return (
    <p className="checked">
      <span className="checked-label">Prices checked</span>
      <span className="checked-date tabular">{value}</span>
    </p>
  );
}

// ---------------------------------------------------------------------------
// Refusal: information, not an error
// ---------------------------------------------------------------------------

function Refusal({ answer }: { answer: string }) {
  return (
    <div className="refusal">
      <p className="refusal-lead">Not on these seven pages</p>
      {answer.trim() && <p className="refusal-text">{answer}</p>}
      <p className="refusal-help">
        A PlacidWay coordinator can answer it directly, and a quote costs nothing.
      </p>
      <a className="action" href={QUOTE_URL} target="_blank" rel="noopener">
        Request a free quote
        <Arrow className="inline-arrow" />
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Rail
// ---------------------------------------------------------------------------

function Contents() {
  return (
    <nav className="rail-block" aria-label="On this page">
      <p className="rail-label">On this page</p>
      <ol className="contents">
        <li>
          <a href="#title">The guide</a>
        </li>
        <li>
          <a href="#composer">Ask a question</a>
        </li>
        <li>
          <a href="#about">About the answers</a>
        </li>
      </ol>
    </nav>
  );
}

function Disclaimer() {
  return (
    <section className="rail-block" id="about" aria-labelledby="about-title">
      <h2 className="rail-label" id="about-title">
        About the answers
      </h2>
      <p className="rail-text">
        Answers are general information, not medical advice. They come only from the seven
        PlacidWay pages and can be out of date. Talk to your own doctor before choosing any
        treatment, and confirm the price with the clinic before you pay.
      </p>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Screen reader stream
// ---------------------------------------------------------------------------

// The stage, announced once per change. The streaming text itself is not
// pushed into this region chunk by chunk; the finished answer is read from the
// transcript when it is in the reading order.
function Live({ stage, status }: { stage: Stage | null; status: TurnStatus | null }) {
  let text = "";
  if (status === "streaming" && stage) text = STAGE_TEXT[stage];
  else if (status === "error") text = "The guide could not reach its pages.";
  else if (status === "stopped") text = "Stopped.";
  return (
    <p className="sr-only" role="status" aria-live="polite" aria-atomic="true">
      {text}
    </p>
  );
}

// ---------------------------------------------------------------------------
// Composer: docked, grows to a limit, Enter sends, Shift+Enter breaks
// ---------------------------------------------------------------------------

function Composer({
  value,
  busy,
  onChange,
  onSend,
  onStop,
}: {
  value: string;
  busy: boolean;
  onChange: (v: string) => void;
  onSend: () => void;
  onStop: () => void;
}) {
  const box = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 152)}px`;
  }, [value]);

  const canSend = value.trim().length > 0 && !busy;

  return (
    <div className="dock">
      <form
        id="composer"
        className="composer"
        onSubmit={(event) => {
          event.preventDefault();
          if (canSend) onSend();
        }}
      >
        <label className="sr-only" htmlFor="message">
          Your question about treatment in Tijuana
        </label>
        <textarea
          id="message"
          ref={box}
          name="message"
          rows={1}
          value={value}
          disabled={busy}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              if (canSend) onSend();
            }
          }}
          placeholder="Ask about prices, a programme, the doctors or the trip"
          autoComplete="off"
          spellCheck
          enterKeyHint="send"
        />
        {busy ? (
          <button type="button" className="stop" onClick={onStop} aria-label="Stop the answer">
            <span className="stop-square" aria-hidden="true" />
            <span className="stop-word">Stop</span>
          </button>
        ) : (
          <button type="submit" className="send" disabled={!canSend} aria-label="Send your question">
            <span className="send-word">Ask</span>
            <Arrow className="send-arrow" />
          </button>
        )}
      </form>
      <p className="hint">
        <kbd>Enter</kbd> sends, <kbd>Shift</kbd> + <kbd>Enter</kbd> starts a new line. Answers are
        general information, not medical advice.
      </p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Footer: the quiet system line
// ---------------------------------------------------------------------------

function Footer({ health }: { health: HealthState }) {
  const data = health.data;
  let line: string;
  if (health.state === "loading") line = "Checking the pages…";
  else if (health.state === "down" || !data) line = "The guide is not connected right now.";
  else {
    const parts: string[] = [];
    if (typeof data.pages === "number") parts.push(`${data.pages} pages`);
    if (typeof data.chunks === "number") parts.push(`${data.chunks} passages`);
    if (typeof data.prices === "number") parts.push(`${data.prices} prices`);
    if (data.model) parts.push(data.model);
    line = parts.join(" · ");
  }

  return (
    <footer className="foot">
      <div className="foot-inner">
        <p className="foot-line">
          <span className={`dot${health.state === "ok" ? " dot-ok" : ""}`} aria-hidden="true" />
          <span className="sr-only">{health.state === "ok" ? "Connected: " : ""}</span>
          <span className="tabular">{line}</span>
        </p>
        <p className="foot-note">
          PlacidWay treatment guide. ITC Immunity Therapy Center, Tijuana. General information, not
          medical advice.
        </p>
      </div>
    </footer>
  );
}

// ---------------------------------------------------------------------------
// Icons, inline, two weights only
// ---------------------------------------------------------------------------

function Arrow({ className }: { className?: string }) {
  return (
    <svg className={`arrow ${className ?? ""}`} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path d="M3 8h9.2M8.6 4.2 12.4 8l-3.8 3.8" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

function Thumb({ up }: { up?: boolean }) {
  return (
    <svg className="thumb" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <g transform={up ? undefined : "rotate(180 10 10)"}>
        <path
          d="M6.6 9.1 9.4 3.9a1.5 1.5 0 0 1 1.9-.7 1.5 1.5 0 0 1 .9 1.7l-.5 2.6h3.1a1.3 1.3 0 0 1 1.3 1.6l-1 4.6a1.3 1.3 0 0 1-1.3 1H6.6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
        <rect x="2.8" y="9.1" width="3.1" height="5.6" rx="0.6" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </g>
    </svg>
  );
}
