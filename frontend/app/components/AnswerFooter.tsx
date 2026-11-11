import { useEffect, useRef, useState } from "react";
import type { DonePayload } from "../lib/types";
import { Copy as CopyIcon, Thumb } from "./Icons";
import type { Turn } from "./conversation";

// Under the answer: the one text escape hatch (copy), the rating, and the small
// true facts about the answer. Nothing here competes with the answer itself.
export function AnswerFooter({
  turn,
  done,
  onRate,
}: {
  turn: Turn;
  done: DonePayload;
  onRate: (rating: 1 | -1) => void;
}) {
  const { copied, copy } = useCopy(done.answer);
  const rated = turn.rating !== null;

  return (
    <div className="answer-foot">
      <div className="answer-tools">
        <button type="button" className="tool" onClick={copy}>
          <CopyIcon done={copied} />
          {copied ? "Copied" : "Copy answer"}
        </button>

        <span className="rate-group">
          <span className="rate-question" id={`fb-${turn.id}`}>
            Useful?
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
        </span>

        <span className="rate-note" role="status">
          {rated ? (turn.ratingFailed ? "Thanks. It could not be saved just now." : "Thanks, noted.") : ""}
        </span>
      </div>

      <p className="provenance">
        <span>
          From <span className="tabular">{done.sources.length}</span>{" "}
          {done.sources.length === 1 ? "page" : "pages"}
        </span>
        <span className="provenance-sep" aria-hidden="true" />
        <span>
          Answered in <span className="tabular">{seconds(done.latency_ms)}</span> s
        </span>
        {done.prices_checked_at && (
          <>
            <span className="provenance-sep" aria-hidden="true" />
            <span>Prices checked <span className="tabular">{done.prices_checked_at}</span></span>
          </>
        )}
      </p>
    </div>
  );
}

function seconds(ms: number): string {
  // A backend-side error reports 0; showing "0.0 s" would read as a fast answer.
  return ms > 0 ? (ms / 1000).toFixed(1) : "–";
}

function useCopy(value: string) {
  const [copied, setCopied] = useState(false);
  const timer = useRef<number | null>(null);

  useEffect(
    () => () => {
      if (timer.current) window.clearTimeout(timer.current);
    },
    [],
  );

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      if (timer.current) window.clearTimeout(timer.current);
      timer.current = window.setTimeout(() => setCopied(false), 2000);
    } catch {
      // Clipboard permission can be refused. The text is selectable on the page,
      // so there is nothing to break and a button label would be a dead end.
    }
  };

  return { copied, copy };
}
