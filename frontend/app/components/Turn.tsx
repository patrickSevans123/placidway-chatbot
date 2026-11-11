import { useState } from "react";
import { STAGE_TEXT, type VisibleStage } from "../lib/brand";
import { extractPrice, withoutPriceSentence } from "../lib/price";
import type { DonePayload, Source } from "../lib/types";
import { AnswerProse, StreamingText } from "./AnswerProse";
import { AnswerFooter } from "./AnswerFooter";
import { PricePanel } from "./PricePanel";
import { QuoteForm } from "./QuoteForm";
import { FailedNotice, LimitedNotice, Refusal, ServiceFailed, StoppedNotice } from "./States";
import { Sources } from "./Sources";
import type { Turn } from "./conversation";

const STAGES: VisibleStage[] = ["retrieving", "drafting"];

// One question and everything the page says about it. No bubble: the question
// is a small label and the answer flows as document prose, which is what this is.
export function TurnView({
  turn,
  lit,
  onCite,
  onRetry,
  onRate,
  sessionId,
}: {
  turn: Turn;
  lit: string | null;
  onCite: (sourceId: string) => void;
  onRetry: () => void;
  onRate: (rating: 1 | -1) => void;
  sessionId: string | null;
}) {
  // The quote form is shared by every state that can end with "ask a person":
  // a refusal, a rate limit, and a normal answer. Its open state lives here so
  // one turn never shows two forms.
  const [quoteOpen, setQuoteOpen] = useState(false);
  const quote = (
    <QuoteForm
      open={quoteOpen}
      onToggle={() => setQuoteOpen((open) => !open)}
      sessionId={sessionId}
      question={turn.question}
    />
  );

  return (
    <article className="turn" aria-labelledby={`q-${turn.id}`}>
      <p className="turn-question" id={`q-${turn.id}`}>
        {turn.question}
      </p>

      {turn.status === "streaming" && <Streaming turn={turn} />}
      {turn.status === "stopped" && <StoppedNotice onRetry={onRetry} />}
      {turn.status === "error" && <FailedNotice onRetry={onRetry} offline={false} />}
      {turn.status === "offline" && <FailedNotice onRetry={onRetry} offline />}
      {turn.status === "limited" && (
        <LimitedNotice retryAfter={turn.retryAfter} onRetry={onRetry}>
          {quote}
        </LimitedNotice>
      )}
      {turn.status === "done" && turn.done && (
        <Finished
          turn={turn}
          done={turn.done}
          lit={lit}
          onCite={onCite}
          onRetry={onRetry}
          onRate={onRate}
          quote={quote}
          quoteOpen={quoteOpen}
        />
      )}
    </article>
  );
}

// The stage line is the only thing on screen for the first few seconds, so it
// stays visible while the text arrives rather than being replaced the moment the
// first token lands. `verifying` takes milliseconds on the server, so it is not
// shown here; the finished answer carries the check line instead.
function Streaming({ turn }: { turn: Turn }) {
  const stage: VisibleStage = turn.stage === "drafting" ? "drafting" : "retrieving";
  const at = STAGES.indexOf(stage);
  return (
    <>
      <div className="stage" role="status" aria-live="polite" aria-atomic="true">
        <span className="stage-track" aria-hidden="true">
          {STAGES.map((name, i) => (
            <span key={name} className="stage-step" data-state={i < at ? "done" : i === at ? "now" : "next"} />
          ))}
        </span>
        <span className="stage-word">{STAGE_TEXT[stage]}</span>
      </div>
      {turn.text.trim() ? <StreamingText text={turn.text} /> : <p className="waiting">Reading the seven pages…</p>}
    </>
  );
}

function Finished({
  turn,
  done,
  lit,
  onCite,
  onRetry,
  onRate,
  quote,
  quoteOpen,
}: {
  turn: Turn;
  done: DonePayload;
  lit: string | null;
  onCite: (sourceId: string) => void;
  onRetry: () => void;
  onRate: (rating: 1 | -1) => void;
  quote: React.ReactNode;
  quoteOpen: boolean;
}) {
  const [bodyOpen, setBodyOpen] = useState(true);
  const sources: Source[] = Array.isArray(done.sources) ? done.sources : [];

  // `intent: "error"` with no pages is the backend saying its own generation
  // failed. That is not the same as the pages not covering the question.
  if (done.intent === "error" && sources.length === 0) {
    return <ServiceFailed onRetry={onRetry} />;
  }

  const showQuote = done.show_lead_form || !done.grounded;

  if (!done.grounded) {
    return (
      <>
        <Refusal answer={done.answer} />
        {showQuote && quote}
        <AnswerFooter turn={turn} done={done} onRate={onRate} />
      </>
    );
  }

  // Derived from the finished, grounded text, never stored: the panel can then
  // never disagree with the prose it was lifted from.
  const price = extractPrice(done.answer);
  const priceSource = price?.cite ? (sources[price.cite - 1] ?? null) : null;
  // The panel states the figure, so the sentence it was lifted from is cut from
  // the prose below. A sentence holding a second price is kept whole.
  const rest = price ? withoutPriceSentence(done.answer, price) : done.answer;

  return (
    <>
      {price && (
        <PricePanel
          price={price}
          source={priceSource}
          onCite={onCite}
          bodyOpen={bodyOpen}
          hasBody={rest.trim().length > 0}
          onToggle={() => setBodyOpen((open) => !open)}
        />
      )}

      {rest.trim() && (!price || bodyOpen) && (
        <AnswerProse markdown={rest} sources={sources} onCite={onCite} />
      )}

      {/* `replace` fires on nearly every answer, because the guard collapses
          repeated pages and renumbers the citations. It is not a signal that a
          figure was removed, so the page does not claim one. What it can say for
          certain is that the body it shows is the checked one. */}
      <p className="checked-line">
        <span className="checked-mark" aria-hidden="true" />
        This answer was checked against the pages before it was shown.
      </p>

      <AnswerFooter turn={turn} done={done} onRate={onRate} />
      {showQuote && quote}
      <Sources sources={sources} lit={lit} onCite={onCite} />
    </>
  );
}
