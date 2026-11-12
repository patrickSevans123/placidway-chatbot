import { CORPUS, PAGES } from "../lib/brand";

// The contents page of the dossier. It is the one tinted surface on the page, and
// it exists only before the first question: it says which seven pages the
// answers are written from, by name, so the claim can be checked by eye. Once an
// answer is on screen this column belongs to the citation margin instead.
export function Contents() {
  return (
    <aside className="contents" aria-labelledby="contents-title">
      <h2 className="contents-label" id="contents-title">
        The seven pages
      </h2>

      <ol className="contents-list">
        {PAGES.map((page, i) => (
          <li className="contents-row" key={page.title}>
            <span className="contents-num tabular" aria-hidden="true">
              {String(i + 1).padStart(2, "0")}
            </span>
            <span className="contents-body">
              <span className="contents-title">{page.title}</span>
              <span className="contents-note">{page.note}</span>
            </span>
          </li>
        ))}
      </ol>

      <p className="contents-foot">
        <span className="tabular">{CORPUS.passages}</span> passages ·{" "}
        <span className="tabular">{CORPUS.prices}</span> prices ·{" "}
        <span className="tabular">{CORPUS.answers}</span> answers
      </p>
    </aside>
  );
}
