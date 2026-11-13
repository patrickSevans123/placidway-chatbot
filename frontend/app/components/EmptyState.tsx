import { CORPUS, PRICES_CHECKED, PROMPTS } from "../lib/brand";

// Before the first question: a greeting, and three questions this guide can
// actually answer, each of which sends the moment it is clicked. The corpus is
// named once, underneath, so the boundary of what can be answered is on screen
// before anything is typed.
export function Opening({ onPick }: { onPick: (q: string) => void }) {
  return (
    <section className="opening" aria-labelledby="opening-title">
      <h1 className="opening-title" id="opening-title">
        Ask about treatment in Tijuana.
      </h1>
      <p className="opening-lede">
        Prices, what each programme includes, the doctors, or the trip. Answers come only from the
        seven PlacidWay pages they cite, and they are general information rather than medical
        advice.
      </p>

      <div className="chips">
        {PROMPTS.map((prompt) => (
          <button
            key={prompt.question}
            type="button"
            className="chip"
            onClick={() => onPick(prompt.question)}
          >
            <span className="chip-mark" aria-hidden="true" />
            <span>{prompt.question}</span>
          </button>
        ))}
      </div>

      <p className="opening-note">
        <span className="tabular">{CORPUS.pages}</span> pages
        <span className="dot" />
        <span className="tabular">{CORPUS.passages}</span> passages
        <span className="dot" />
        <span className="tabular">{CORPUS.prices}</span> prices
        <span className="dot" />
        Prices checked <span className="tabular">{PRICES_CHECKED}</span>
      </p>
    </section>
  );
}
