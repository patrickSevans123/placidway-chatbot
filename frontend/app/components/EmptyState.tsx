import { PRICES_CHECKED, PROMPTS, TIERS } from "../lib/brand";
import { Arrow } from "./Icons";

// The opening is the dossier's first page, not a starter grid: the priced
// schedule is the largest thing on it, then three questions set as rows. The
// headline and the lede above live in ChatSurface.
export function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="empty">
      <section className="docket" aria-labelledby="docket-title">
        <p className="docket-head" id="docket-title">
          Programme · total for three weeks
        </p>

        <dl className="docket-list">
          {TIERS.map((tier) => (
            <div className="docket-row" key={tier.label}>
              <dt className="docket-term">{tier.label}</dt>
              <dd className="docket-value">
                <span className="docket-amount tabular">{tier.amount}</span>
                <span className="docket-cur">USD</span>
              </dd>
            </div>
          ))}
        </dl>

        <p className="docket-note">
          Add-ons are priced separately. Listed on the ITC package pages and checked{" "}
          <span className="tabular">{PRICES_CHECKED}</span>. Confirm the price with the clinic
          before you pay.
        </p>
      </section>

      <section className="starters" aria-labelledby="starters-title">
        <h3 className="starters-head" id="starters-title">
          Start with a question
        </h3>
        <ul className="prompt-list">
          {PROMPTS.map((prompt, i) => (
            <li key={prompt.question}>
              <button type="button" className="prompt" onClick={() => onPick(prompt.question)}>
                <span className="prompt-num tabular" aria-hidden="true">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="prompt-body">
                  <span className="prompt-q">{prompt.question}</span>
                  <span className="prompt-note">{prompt.note}</span>
                </span>
                <Arrow className="prompt-arrow" />
              </button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
