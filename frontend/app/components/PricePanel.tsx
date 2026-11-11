import { formatAmount, type PriceLine } from "../lib/price";
import type { Source } from "../lib/types";
import { Chevron } from "./Icons";

// The qualifier runs on from "USD" in the same line, so only its first letter is
// lowered: "The package price" reads as the rest of that phrase, not a new
// sentence. `text-transform` would also lowercase proper nouns, so it is done on
// the string instead.
function midSentence(text: string): string {
  return text.charAt(0).toLowerCase() + text.slice(1);
}

// The house convention, copied from their package page: the figure, the currency
// small beside it, and a quiet qualifier on the same baseline, reading the way
// their "Price starting from" does. The figure is the largest thing on screen.
export function PricePanel({
  price,
  source,
  onCite,
  bodyOpen,
  hasBody,
  onToggle,
}: {
  price: PriceLine;
  source: Source | null;
  onCite: (sourceId: string) => void;
  bodyOpen: boolean;
  hasBody: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="price">
      <p className="price-figure">
        <span className="price-amount tabular">{formatAmount(price.amount)}</span>
        <span className="price-currency">{price.currency}</span>
        <span className="price-qualifier">
          {midSentence(price.qualifier)}
          {source && price.cite !== null && (
            <>
              {" "}
              <a
                className="cite price-cite"
                href={`#source-${source.id}`}
                aria-label={`Price source ${price.cite}: ${source.title}`}
                onClick={(event) => {
                  event.preventDefault();
                  onCite(source.id);
                }}
              >
                <span aria-hidden="true">{price.cite}</span>
              </a>
            </>
          )}
        </span>
      </p>

      {source && <p className="price-from">From {source.title}</p>}

      {hasBody && (
        <button type="button" className="price-toggle" onClick={onToggle} aria-expanded={bodyOpen}>
          {bodyOpen ? "Hide what else the page says" : "What else the page says"}
          <Chevron open={bodyOpen} />
        </button>
      )}
    </div>
  );
}
