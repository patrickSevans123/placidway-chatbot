import { useEffect, useRef } from "react";
import { Arrow, StopSquare } from "./Icons";

// A field, not a message box. Fixed to the bottom of the window, one hairline
// border, a coral filled button the same shape as their hero call to action.
export function Composer({
  value,
  busy,
  onChange,
  onSend,
  onStop,
  onHeight,
}: {
  value: string;
  busy: boolean;
  onChange: (value: string) => void;
  onSend: () => void;
  onStop: () => void;
  /** Reports the composer's own height so the page can keep a gap under it. */
  onHeight: (px: number) => void;
}) {
  const box = useRef<HTMLTextAreaElement>(null);
  const root = useRef<HTMLDivElement>(null);

  // Grow with the text up to a cap, then scroll inside the field. Never wider
  // than the field, which is what keeps a long pasted question from overflowing
  // the page sideways on a phone.
  useEffect(() => {
    const el = box.current;
    if (!el) return;
    el.style.height = "auto";
    const next = Math.min(el.scrollHeight, 148);
    el.style.height = `${next}px`;
  }, [value]);

  useEffect(() => {
    const el = root.current;
    if (!el) return;
    const report = () => onHeight(el.offsetHeight);
    report();
    const observer = new ResizeObserver(report);
    observer.observe(el);
    return () => observer.disconnect();
  }, [onHeight]);

  const canSend = value.trim().length > 0 && !busy;

  return (
    <div className="composer-dock" ref={root}>
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
          readOnly={busy}
          onChange={(event) => onChange(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
              event.preventDefault();
              if (canSend) onSend();
            }
          }}
          placeholder="Type a question"
          autoComplete="off"
          spellCheck
          enterKeyHint="send"
        />

        {busy ? (
          <button type="button" className="composer-button composer-stop" onClick={onStop}>
            <StopSquare />
            <span className="composer-button-word">Stop</span>
            <span className="sr-only"> the answer</span>
          </button>
        ) : (
          <button type="submit" className="composer-button" disabled={!canSend}>
            <span className="composer-button-word">Ask</span>
            <Arrow className="composer-arrow" />
          </button>
        )}
      </form>

      <p className="composer-hint">
        <kbd>Enter</kbd> sends · <kbd>Shift</kbd> + <kbd>Enter</kbd> adds a line · Answers are
        general information, not medical advice.
      </p>
    </div>
  );
}
