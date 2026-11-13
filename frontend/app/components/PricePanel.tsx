import { PACKAGE_PAGE, PRICES_CHECKED, TIERS } from "../lib/brand";

// The two programme prices, beside an answer that cites the page they are
// printed on. This is the corpus's own record, not a figure lifted out of the
// model's prose: the numbers are the ones the index carries, and the note names
// the page and the date they were checked on.
export function PricePanel({ turnId }: { turnId: number }) {
  return (
    <section className="price-record" aria-labelledby={`price-record-${turnId}`}>
      <h3 className="label" id={`price-record-${turnId}`}>
        Package prices · three weeks
      </h3>

      <dl className="price-list">
        {TIERS.map((tier) => (
          <div className="price-row" key={tier.label}>
            <dt className="price-term">{tier.label}</dt>
            <dd>
              <span className="price-value tabular">{tier.amount}</span>
              <span className="price-unit">USD</span>
            </dd>
          </div>
        ))}
      </dl>

      <p className="price-note">
        Printed on the{" "}
        <a href={PACKAGE_PAGE.url} target="_blank" rel="noopener">
          {PACKAGE_PAGE.title.toLowerCase()} page
          <span className="sr-only"> (opens in a new tab)</span>
        </a>
        , checked <span className="tabular">{PRICES_CHECKED}</span>. Confirm the price with the
        clinic before you pay.
      </p>
    </section>
  );
}
