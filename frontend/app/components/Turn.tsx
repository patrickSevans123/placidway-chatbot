import { useState } from "react";
import { PACKAGE_PAGE, STAGE_TEXT, type VisibleStage } from "../lib/brand";
import { statesAmount } from "../lib/money";
import type { DonePayload, Source } from "../lib/types";
import { AnswerProse, StreamingText } from "./AnswerProse";
import { AnswerFooter } from "./AnswerFooter";
import { PricePanel } from "./PricePanel";
import { QuoteForm } from "./QuoteForm";
import { FailedNotice, LimitedNotice, Refusal, ServiceFailed, StoppedNotice } from "./States";
import { Sources } from "./Sources";
import type { Turn } from "./conversation";

const STAGES: VisibleStage[] = ["retrieving", "drafting"];

// One question and everything the page says about it. The question is a bubble
// on the right, because it is the visitor speaking; the answer is a column of
// printed text, because it carries citations, a sources disclosure, a price
// record and a form.
export function TurnView({
  turn,
  litId,
  onCite,
  onRetry,
  onRate,
  sessionId,
}: {
  turn: Turn;
  litId: string | null;
  onCite: (sourceId: string) => void;
  onRetry: () => void;
  onRate: (rating: 1 | -1) => void;
  sessionId: string | null;
}) {
  // The quote form is shared by every state that can end with "ask a person":
  // a refusal, a rate limit, and a normal answer. Its open state lives here so
  // one turn never shows two forms.
  const [quoteOpen, setQuoteOpen] = useState(false);
  // The pages stay folded until something asks for them: a citation click, or
  // the reader's own click on the summary.
  const [sourcesOpen, setSourcesOpen] = useState(false);

  const quote = (
    <QuoteForm
      open={quoteOpen}
      onToggle={() => setQuoteOpen((open) => !open)}
      sessionId={sessionId}
      question={turn.question}
    />
  );

  const done = turn.status === "done" ? turn.done : null;
  const sources: Source[] =
    done && done.grounded && !(done.intent === "error" && (done.sources ?? []).length === 0)
      ? Array.isArray(done.sources)
        ? done.sources
        : []
      : [];

  // A citation click both lights its page and unfolds the list it lives in: with
  // no rail beside the column, the note under the answer is the only place the
  // light can be seen.
  const cite = (sourceId: string) => {
    setSourcesOpen(true);
    onCite(sourceId);
  };

  return (
    <article className="turn" aria-labelledby={`q-${turn.id}`}>
      <h2 className="ask" id={`q-${turn.id}`}>
        {turn.question}
      </h2>

      <div className="reply">
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
            sources={sources}
            litId={litId}
            sourcesOpen={sourcesOpen}
            onToggleSources={setSourcesOpen}
            onCite={cite}
            onRetry={onRetry}
            onRate={onRate}
            quote={quote}
          />
        )}
      </div>
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
  sources,
  litId,
  sourcesOpen,
  onToggleSources,
  onCite,
  onRetry,
  onRate,
  quote,
}: {
  turn: Turn;
  done: DonePayload;
  sources: Source[];
  litId: string | null;
  sourcesOpen: boolean;
  onToggleSources: (open: boolean) => void;
  onCite: (sourceId: string) => void;
  onRetry: () => void;
  onRate: (rating: 1 | -1) => void;
  quote: React.ReactNode;
}) {
  // `intent: "error"` with no pages is the backend saying its own generation
  // failed. That is not the same as the pages not covering the question.
  if (done.intent === "error" && sources.length === 0) {
    return <ServiceFailed onRetry={onRetry} />;
  }

  const showQuote =
    done.show_lead_form ||
    !done.grounded ||
    // Some answers end by telling the reader to request a quote, without the
    // backend setting the flag (a `general` intent that runs out of page). A
    // sentence pointing at a control that is not on the page is worse than no
    // sentence, so the control follows the words.
    /free quote/i.test(done.answer);

  // `out_of_scope` comes back grounded with no cited page: the model answers an
  // off-topic question with an apology. Rendering it as a normal answer claims
  // it was "checked against the pages" when nothing was cited, so it is framed
  // as a boundary notice instead, without the quote pitch (a coordinator cannot
  // answer a question about the weather).
  if (done.intent === "out_of_scope") {
    return (
      <>
        <div className="refusal">
          <p className="refusal-lead">Outside these pages</p>
          <p className="refusal-text">{done.answer}</p>
          <p className="refusal-help">
            This guide covers ITC&rsquo;s treatments, prices, doctors and the trip to Tijuana.
          </p>
        </div>
        <AnswerFooter turn={turn} done={done} onRate={onRate} />
      </>
    );
  }

  if (!done.grounded) {
    return (
      <>
        <Refusal answer={done.answer} />
        <AnswerFooter turn={turn} done={done} onRate={onRate} />
        {showQuote && quote}
      </>
    );
  }

  return (
    <>
      {/* The body is the markdown the API returned, whole. Every figure keeps
          the sentence the model wrote it in, next to the page it cited. */}
      <AnswerProse markdown={done.answer} sources={sources} onCite={onCite} />

      {/* `replace` fires on nearly every answer, because the guard collapses
          repeated pages and renumbers the citations. It is not a signal that a
          figure was removed, so the page does not claim one. What it can say for
          certain is that the body it shows is the checked one. */}
      <p className="checked-line">
        <span className="checked-mark" aria-hidden="true" />
        This answer was checked against the pages before it was shown.
      </p>

      {/* The boundary travels with the answer that needs it, and only while the
          API asks for it. A permanent line under every reply is the pattern this
          replaces. */}
      {done.show_disclaimer && (
        <p className="disclaimer">
          <strong>General information, not medical advice.</strong> Talk to a doctor about your own
          case before you decide on treatment.
        </p>
      )}

      <AnswerFooter turn={turn} done={done} onRate={onRate} />

      {sources.length > 0 && (
        <Sources
          sources={sources}
          open={sourcesOpen}
          onToggle={onToggleSources}
          lit={litId}
          onCite={onCite}
        />
      )}

      {/* The record only appears under an answer that states a figure and cites
          the page the record is printed on. On "who are the doctors" or a
          recovery-time question the two package prices are numbers the answer
          never mentions; on an adrenal price question they would be the wrong
          package's prices, printed under a note naming a different page. */}
      {statesAmount(done.answer) && sources.some((source) => source.url === PACKAGE_PAGE.url) && (
        <PricePanel turnId={turn.id} />
      )}

      {showQuote && quote}
    </>
  );
}
