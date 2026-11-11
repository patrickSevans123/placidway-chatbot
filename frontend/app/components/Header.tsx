import { PAGE_COUNT } from "../lib/brand";
import { Arrow } from "./Icons";

// White bar with a hairline under it. The wordmark is set as text in coral, not
// an image: their mark is not ours to redraw, and a text wordmark cannot 404.
export function Header({ onNew, showNew }: { onNew: () => void; showNew: boolean }) {
  return (
    <header className="top">
      <div className="top-inner">
        <a className="brand" href="./" aria-label="PlacidWay treatment guide, start a new question">
          <span className="brand-name">PlacidWay</span>
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
