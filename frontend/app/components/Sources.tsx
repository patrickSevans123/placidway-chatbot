import { readableUrl } from "../lib/markdown";
import type { Source } from "../lib/types";
import { Arrow } from "./Icons";

// The source block borrows their "About Package" panel: a titled, hairline-bordered
// block with the rows separated by rules. Each row is a real link to the page.
export function Sources({
  sources,
  lit,
  onCite,
}: {
  sources: Source[];
  lit: string | null;
  onCite: (sourceId: string) => void;
}) {
  if (!sources.length) return null;

  return (
    <section className="sources" aria-labelledby="sources-title">
      <div className="panel-head">
        <h3 className="panel-title" id="sources-title">
          {sources.length === 1 ? "The page this came from" : `The ${sources.length} pages this came from`}
        </h3>
      </div>
      <ol className="source-list">
        {sources.map((source, i) => {
          const active = lit === source.id;
          return (
            <li
              // The id is the target of the [n] links in the answer.
              key={source.id}
              id={`source-${source.id}`}
              className={`source${active ? " is-lit" : ""}`}
              aria-current={active ? "true" : undefined}
              ref={(node) => {
                if (!node) return;
                // A citation click scrolls the card into view once; the class
                // change is what re-runs this for a second click on the same [n].
                if (!active || node.dataset.seen === "1") return;
                node.dataset.seen = "1";
                if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                  node.scrollIntoView({ block: "nearest" });
                } else {
                  node.scrollIntoView({ block: "nearest", behavior: "smooth" });
                }
              }}
              onAnimationEnd={(event) => {
                if (event.target === event.currentTarget) onCite("");
              }}
            >
              <a className="source-link" href={source.url} target="_blank" rel="noopener">
                <span className="source-num tabular" aria-hidden="true">
                  {i + 1}
                </span>
                <span className="source-body">
                  <span className="source-title">
                    {source.title}
                    <Arrow className="inline-arrow" />
                    <span className="sr-only"> (opens in a new tab)</span>
                  </span>
                  <span className="source-meta">
                    <span className="source-type">{source.page_type}</span>
                    <span className="source-url">{readableUrl(source.url)}</span>
                  </span>
                </span>
              </a>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
