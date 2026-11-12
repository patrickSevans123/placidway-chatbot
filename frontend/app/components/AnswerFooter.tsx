import { useEffect, useRef, useState } from "react";
import type { DonePayload } from "../lib/types";
import { Copy as CopyIcon, Thumb } from "./Icons";
import type { Turn } from "./conversation";

// Under the answer: the one text escape hatch (copy), the rating, and the small
// true facts about the answer. One 12px row, three actions, hairline separators;
// nothing here competes with the answer above it.
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
          {copied ? "Copied" : "Copy"}
        </button>

        <span className="rate-group">
          <span className="rate-question" id={`fb-${turn.id}`}>
            Helpful?
          </span>
          <button
            type="button"
            className="rate"
            aria-label="This answer was helpful"
            aria-describedby={`fb-${turn.id}`}
            aria-pressed={turn.rating === 1}
            disabled={rated}
            onClick={() => onRate(1)}
          >
            <Thumb up />
            <span>Yes</span>
          </button>
          <button
            type="button"
            className="rate"
            aria-label="This answer was not helpful"
            aria-describedby={`fb-${turn.id}`}
            aria-pressed={turn.rating === -1}
            disabled={rated}
            onClick={() => onRate(-1)}
          >
            <Thumb />
            <span>No</span>
          </button>
        </span>

        <span className="rate-note" role="status">
          {rated ? (turn.ratingFailed ? "Thanks. It could not be saved just now." : "Thanks, noted.") : ""}
        </span>
      </div>

      {/* A boundary answer has no page and no measured latency, so the whole
          line is dropped rather than printed as "From 0 pages". */}
      {(done.sources.length > 0 || done.latency_ms > 0) && (
        <p className="provenance">
          <span className="provenance-item">
            From <span className="tabular">{done.sources.length}</span>{" "}
            {done.sources.length === 1 ? "page" : "pages"}
          </span>
          {done.latency_ms > 0 && (
            <span className="provenance-item">
              Answered in <span className="tabular">{seconds(done.latency_ms)}</span> s
            </span>
          )}
          {done.prices_checked_at && (
            <span className="provenance-item">
              Prices checked <span className="tabular">{done.prices_checked_at}</span>
            </span>
          )}
        </p>
      )}
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
