import { useEffect, useRef } from "react";
import type { HealthState } from "./conversation";
import { Arrow, StopSquare } from "./Icons";

// The question field, docked as the last row of the shell. It never floats over
// the thread: the thread ends above it, so the last thing an answer says is
// always reachable.
export function Composer({
  value,
  busy,
  health,
  onChange,
  onSend,
  onStop,
  autoFocus,
}: {
  value: string;
  busy: boolean;
  health: HealthState;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  autoFocus: boolean;
}) {
  const box = useRef<HTMLTextAreaElement>(null);

  // Grow with the text up to a cap, then scroll inside the field. Never wider
  // than the field, which is what keeps a long pasted question from overflowing
  // the page sideways on a phone.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 148)}px`;
  }, [value]);

  // The empty screen puts the cursor in the field, so the first thing a visitor
  // can do is type. A restored conversation does not steal focus.
  useEffect(() => {
    if (autoFocus) box.current?.focus();
  }, [autoFocus]);

  const canSend = value.trim().length > 0 && !busy;

  const status =
    health.state === "loading"
      ? "Checking the answer service…"
      : health.state === "down"
        ? "The answer service is not responding right now."
        : "Answer service ready";

  return (
    <div className="composer-dock">
      <div className="dock-inner">
        <form
          id="composer"
          className="composer"
          onSubmit={(event) => {
            event.preventDefault();
            // An empty field has one useful action: put the cursor in it. The
            // button is never dimmed to look disabled before it is asked to do
            // something it cannot do.
            if (canSend) onSend();
            else box.current?.focus();
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
            readOnly={busy}
            onChange={(event) => onChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
                event.preventDefault();
                if (canSend) onSend();
              }
            }}
            placeholder="Ask about prices or the doctors"
            autoComplete="off"
            spellCheck
            enterKeyHint="send"
          />

          {busy ? (
            <button type="button" className="composer-ask composer-stop" onClick={onStop}>
              <StopSquare />
              <span>Stop</span>
              <span className="sr-only"> the answer</span>
            </button>
          ) : (
            <button type="submit" className="composer-ask">
              <span>Ask</span>
              <Arrow className="composer-arrow" />
            </button>
          )}
        </form>

        <div className="dock-meta">
          <p className="dock-status">
            <span
              className={`status-dot${health.state === "ok" ? " status-ok" : ""}`}
              aria-hidden="true"
            />
            <span>{status}</span>
          </p>
          <p className="composer-hint">
            <kbd>Enter</kbd> sends · <kbd>Shift</kbd> + <kbd>Enter</kbd> adds a line
          </p>
        </div>
      </div>
    </div>
  );
}
