import { hostOf } from "../lib/markdown";
import type { Source } from "../lib/types";
import { Arrow, Chevron } from "./Icons";

// The apparatus of one answer, folded into a disclosure so a chat reply stays a
// reply. The numbered glyphs in the prose are the citation; clicking one opens
// this list and lights the row it points at, and the disclosure can also be
// opened by hand. A native <details>, so the keyboard and the browser's own
// find-in-page reach it without a listener.
export function Sources({
  sources,
  open,
  onToggle,
  lit,
  onCite,
}: {
  sources: Source[];
  open: boolean;
  onToggle: (open: boolean) => void;
  lit: string | null;
  onCite: (sourceId: string) => void;
}) {
  if (!sources.length) return null;

  return (
    <details
      className="sources"
      open={open}
      onToggle={(event) => onToggle(event.currentTarget.open)}
    >
      <summary className="sources-summary">
        <Chevron open={open} />
        <span>Sources</span>
        <span className="sources-count">
          · <span className="tabular">{sources.length}</span>{" "}
          {sources.length === 1 ? "page" : "pages"}
        </span>
      </summary>

      <ol className="source-list">
        {sources.map((source, i) => {
          const active = lit === source.id;
          return (
            <li
              // The id is the target of the [n] links in the answer.
              key={source.id}
              id={`source-${source.id}`}
              className="source"
              data-lit={active}
              aria-current={active ? "true" : undefined}
              ref={(node) => {
                if (!node) return;
                // A citation click brings the note into view once; the data
                // change is what re-runs this for a second click on the same [n].
                if (!active || node.dataset.seen === "1") return;
                node.dataset.seen = "1";
                if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
                  node.scrollIntoView({ block: "nearest" });
                } else {
                  node.scrollIntoView({ block: "nearest", behavior: "smooth" });
                }
              }}
            >
              <a
                className="source-link"
                href={source.url}
                target="_blank"
                rel="noopener"
                onClick={() => onCite(source.id)}
              >
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
                        one unbreakable word, so every shortening ended mid-word.
                        The title above names the page and the link opens it; the
                        whole address is in `title`. */}
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
    </details>
  );
}
