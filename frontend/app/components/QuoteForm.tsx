import { useEffect, useId, useRef, useState } from "react";
import { postLead } from "../lib/lead";
import { Arrow } from "./Icons";

// The free-quote form. It writes to /api/lead, which is the only reason the form
// exists: a coordinator cannot reply to an address that was never sent.
// Open state lives here so the disclosure is one control, not two.
export function QuoteForm({
  open,
  onToggle,
  sessionId,
  question,
}: {
  open: boolean;
  onToggle: () => void;
  sessionId: string | null;
  question: string;
}) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [note, setNote] = useState("");
  const [state, setState] = useState<"idle" | "sending" | "sent" | "problem">("idle");
  const [problem, setProblem] = useState<"email" | "network" | null>(null);
  const fieldId = useId();
  const firstField = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) firstField.current?.focus();
  }, [open]);

  const sent = state === "sent";

  if (!open && !sent) {
    return (
      <button
        type="button"
        className="quote-open"
        onClick={onToggle}
        aria-expanded={false}
        aria-controls={`${fieldId}-panel`}
      >
        Request a free quote
        <Arrow className="inline-arrow" />
      </button>
    );
  }

  if (sent) {
    return (
      <p className="quote-sent" role="status">
        <strong>Thank you.</strong> PlacidWay will reply to {email} about your question.
      </p>
    );
  }

  return (
    <div className="quote" id={`${fieldId}-panel`}>
      <p className="quote-lead">
        Leave your name and email. A PlacidWay coordinator will reply with a price for your case.
      </p>
      <form
        className="quote-form"
        noValidate
        onSubmit={async (event) => {
          event.preventDefault();
          if (state === "sending") return;
          const cleanName = name.trim();
          const cleanEmail = email.trim();
          if (!cleanName || !cleanEmail) {
            setState("problem");
            setProblem(!cleanEmail || !/^\S+@\S+\.\S+$/.test(cleanEmail) ? "email" : "network");
            return;
          }
          setState("sending");
          setProblem(null);
          const result = await postLead({
            session_id: sessionId,
            name: cleanName,
            email: cleanEmail,
            message: note.trim() || question,
          });
          if (result.ok) setState("sent");
          else {
            setState("problem");
            setProblem(result.problem);
          }
        }}
      >
        <div className="quote-field">
          <label htmlFor={`${fieldId}-name`}>Your name</label>
          <input
            id={`${fieldId}-name`}
            ref={firstField}
            name="name"
            type="text"
            autoComplete="name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            aria-invalid={problem === "network" && !name.trim() ? true : undefined}
          />
        </div>
        <div className="quote-field">
          <label htmlFor={`${fieldId}-email`}>Email</label>
          <input
            id={`${fieldId}-email`}
            name="email"
            type="email"
            inputMode="email"
            autoComplete="email"
            placeholder="you@example.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            aria-invalid={problem === "email" ? true : undefined}
            aria-describedby={problem ? `${fieldId}-problem` : undefined}
          />
        </div>
        <div className="quote-field quote-field-wide">
          <label htmlFor={`${fieldId}-note`}>
            Anything to add? <span className="optional">Optional</span>
          </label>
          <textarea
            id={`${fieldId}-note`}
            name="message"
            rows={2}
            value={note}
            onChange={(event) => setNote(event.target.value)}
          />
        </div>

        <div className="quote-actions">
          <button type="submit" className="button button-solid" disabled={state === "sending"}>
            {state === "sending" ? "Sending…" : "Send my question"}
          </button>
          <button type="button" className="quote-close" onClick={onToggle}>
            Not now
          </button>
        </div>

        <p className="quote-note">
          We use these details only to answer your question. Nothing is shared with anyone else.
        </p>
        {problem && (
          <p className="field-problem" id={`${fieldId}-problem`} role="alert">
            {problem === "email"
              ? "Please enter an email address the team can reply to."
              : "That did not send. Check your connection and try again, or open the PlacidWay quote page."}
          </p>
        )}
      </form>
    </div>
  );
}
