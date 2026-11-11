import { STARTERS } from "../lib/brand";
import { Arrow, Icon } from "./Icons";

// Their page pattern, not a hero: a row of bordered cards with thin line icons.
// Each card is a button that submits its own question, so the reader never has
// to copy text out of the page. The headline and lede above live in ChatSurface.
export function EmptyState({ onPick }: { onPick: (q: string) => void }) {
  return (
    <div className="empty">
      <ul className="starters">
        {STARTERS.map((starter) => (
          <li key={starter.question}>
            <button
              type="button"
              className="starter"
              onClick={() => onPick(starter.question)}
            >
              <span className="starter-icon" aria-hidden="true">
                <Icon name={starter.icon} />
              </span>
              <span className="starter-body">
                <span className="starter-q">{starter.question}</span>
                <span className="starter-note">{starter.note}</span>
              </span>
              <Arrow className="starter-arrow" />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
