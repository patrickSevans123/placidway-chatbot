import { formatAmount, type PriceLine } from "../lib/price";
import type { Source } from "../lib/types";
import { Chevron } from "./Icons";

// The figure is the one display object on a price answer. It is set like a
// printed schedule line: a mono caption, the number at display size in tabular
// figures, the qualifier on its own line at reading size, and one hairline under.
// No box, no tint — the size does the work.
//
// The qualifier keeps its capital, because it is a line of its own: "The
// out-patient programme", not a phrase running on from "USD".
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
    <div className="figure">
      <p className="figure-label">Price</p>

      <p className="figure-line">
        <span className="figure-amount tabular">{formatAmount(price.amount)}</span>
        <span className="figure-cur">{price.currency}</span>
        <span className="figure-qualifier">
          {price.qualifier}
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

      {source && <p className="figure-from">From {source.title}</p>}

      {hasBody && (
        <button type="button" className="figure-toggle" onClick={onToggle} aria-expanded={bodyOpen}>
          {bodyOpen ? "Hide what else the pages say" : "What else the pages say"}
          <Chevron open={bodyOpen} />
        </button>
      )}
    </div>
  );
}
