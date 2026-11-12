import { hostOf } from "../lib/markdown";
import type { Source } from "../lib/types";
import { Arrow } from "./Icons";

// The apparatus of the document: which pages the answer above is built from.
// On a wide screen this is the margin column beside the prose, numbered, with a
// hairline between notes and no box around them. On a phone it follows the
// answer as the same numbered list. Each row is a real link to the page.
export function Sources({
  sources,
  lit,
  onCite,
  turnId,
}: {
  sources: Source[];
  lit: string | null;
  onCite: (sourceId: string) => void;
  turnId: number;
}) {
  if (!sources.length) return null;

  return (
    <section className="sources" aria-labelledby={`sources-${turnId}`}>
      <h3 className="sources-head" id={`sources-${turnId}`}>
        {sources.length === 1
          ? "The page this came from"
          : `The ${sources.length} pages this came from`}
      </h3>
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
                // A citation click scrolls the note into view once; the class
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
                  {String(i + 1).padStart(2, "0")}
                </span>
                <span className="source-body">
                  <span className="source-title">
                    {source.title}
                    <Arrow className="inline-arrow" />
                    <span className="sr-only"> (opens in a new tab)</span>
                  </span>
                  <span className="source-meta">
                    <span className="source-type">{source.page_type}</span>
                    {/* The domain, never a shortened path: this package's slug is
                        one unbreakable word 324px wide, so every shortening ended
                        mid-word ("/Alte…"). The title above names the page and the
                        link opens it; the whole address is in `title` on hover.
                        Not read aloud, because the title is the link's name. */}
                    <span className="source-url" title={source.url} aria-hidden="true">
                      {hostOf(source.url)}
                    </span>
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
