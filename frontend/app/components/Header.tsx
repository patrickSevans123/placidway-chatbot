import { PAGE_COUNT } from "../lib/brand";
import { Arrow } from "./Icons";

// The mark is their own artwork, self-hosted at 123x62 (their 2:1 proportion) so
// the bar is the same height before and after the file arrives. Their coral
// wordmark is not redrawn as text and not hotlinked: one PNG in public/, one
// optional 2x for retina.
export function Header({ onNew, showNew }: { onNew: () => void; showNew: boolean }) {
  return (
    <header className="top">
      <div className="top-inner">
        <a className="brand" href="./" aria-label="PlacidWay treatment guide, start a new question">
          <img
            className="brand-logo"
            src="/placidway-logo.png"
            srcSet="/placidway-logo.png 1x, /placidway-logo@2x.png 2x"
            width={123}
            height={62}
            alt="PlacidWay"
            fetchPriority="high"
            decoding="async"
          />
          <span className="brand-rule" aria-hidden="true" />
          <span className="brand-sub">Treatment guide</span>
        </a>

        <nav className="top-actions" aria-label="Site">
          {showNew && (
            <button type="button" className="top-new" onClick={onNew}>
              New question
            </button>
          )}
          <a
            className="top-link"
            href="https://www.placidway.com/"
            target="_blank"
            rel="noopener"
          >
            placidway.com
            <span className="sr-only"> (opens in a new tab)</span>
            <Arrow className="tiny" />
          </a>
        </nav>
      </div>
      <p className="sr-only">
        Answers use {PAGE_COUNT} PlacidWay pages about the ITC Immunity Therapy Center.
      </p>
    </header>
  );
}
