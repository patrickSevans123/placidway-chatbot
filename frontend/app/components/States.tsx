import { QUOTE_URL } from "../lib/brand";

// Plain, calm notices. Each one says what happened and what the reader can do
// next; none of them is a spinner with no words beside it.

export function StoppedNotice({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="notice">
      <p className="notice-title">You stopped this answer.</p>
      <p className="notice-text">Nothing below was finished, so it is not shown.</p>
      <button type="button" className="button button-quiet" onClick={onRetry}>
        Ask it again
      </button>
    </div>
  );
}

export function FailedNotice({ onRetry, offline }: { onRetry: () => void; offline: boolean }) {
  return (
    <div className="notice">
      <p className="notice-title">
        {offline ? "You are offline." : "The guide could not be reached."}
      </p>
      <p className="notice-text">
        {offline
          ? "Your phone or computer has lost its connection, so the answer could not be loaded."
          : "Something between this page and its answers did not respond. Your question was not lost."}
      </p>
      <button type="button" className="button button-solid" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}

export function LimitedNotice({
  retryAfter,
  onRetry,
  children,
}: {
  retryAfter: number | null;
  onRetry: () => void;
  /** The quote form, so a limited reader still has one way forward. */
  children?: React.ReactNode;
}) {
  const waits = retryAfter !== null && retryAfter > 0;
  return (
    <div className="notice">
      <p className="notice-title">Too many questions just now.</p>
      <p className="notice-text">
        {waits
          ? `Please wait about ${formatWait(retryAfter)} and ask again. This keeps the guide available to everyone.`
          : "Please wait a minute and ask again. This keeps the guide available to everyone."}
      </p>
      <div className="notice-actions">
        <button type="button" className="button button-solid" onClick={onRetry}>
          Ask it again
        </button>
        {children}
      </div>
    </div>
  );
}

function formatWait(seconds: number): string {
  if (seconds < 90) return `${Math.max(1, Math.round(seconds))} seconds`;
  const minutes = Math.round(seconds / 60);
  return minutes === 1 ? "a minute" : `${minutes} minutes`;
}

// The refusal is information, not an error: no red, no alarm icon. It says what
// the pages do not cover, then offers the one honest way forward.
export function Refusal({ answer }: { answer: string }) {
  return (
    <div className="refusal">
      <p className="refusal-lead">Not covered by these pages</p>
      {answer.trim() && <p className="refusal-text">{answer}</p>}
      <p className="refusal-help">
        A PlacidWay coordinator can answer it directly, and a quote costs nothing.
      </p>
      <a className="button button-solid" href={QUOTE_URL} target="_blank" rel="noopener">
        Request a free quote
        <span className="sr-only"> (opens in a new tab)</span>
      </a>
    </div>
  );
}

// Shown when the answer service itself failed. The backend sends this as a
// grounded:false answer, so it has to be told apart from a normal refusal.
export function ServiceFailed({ onRetry }: { onRetry: () => void }) {
  return (
    <div className="notice">
      <p className="notice-title">Something went wrong on our side.</p>
      <p className="notice-text">
        The question did not reach the answers. You can try it again, or ask a coordinator with the
        free quote form below.
      </p>
      <button type="button" className="button button-quiet" onClick={onRetry}>
        Try again
      </button>
    </div>
  );
}
