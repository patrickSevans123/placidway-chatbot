// The date the price list was last confirmed. It is written once here so the
// trust line, the panel and the footer cannot drift apart.
const PRICES_CHECKED = "11 Nov 2026";

export function guideDate(): string {
  return PRICES_CHECKED;
}

const PAGES = [
  { title: "Clinic profile", note: "The centre, its doctors and its facilities" },
  { title: "Adenocarcinoma package", note: "Including the out- and in-patient prices" },
  { title: "Adrenal cancer package", note: "Treatments and what they include" },
  { title: "Anal cancer package", note: "Treatments and what they include" },
  { title: "Clinic videos", note: "Linked from the centre's profile" },
  { title: "Price list", note: "Each treatment, priced separately" },
  { title: "Price comparison", note: "Alternative medicine abroad, by country" },
];

// Their accreditations row has no honest equivalent here, so the place where it
// would sit holds the thing that is true: which pages the answers come from.
export function GuidePanel() {
  return (
    <aside className="guide" aria-labelledby="guide-title">
      <div className="panel-head">
        <h2 className="panel-title" id="guide-title">
          What this guide reads
        </h2>
      </div>
      <div className="guide-body">
        <p className="guide-text">
          If a question is not covered by these pages, the guide says so rather than guessing.
        </p>
        <ol className="guide-pages">
          {PAGES.map((page, i) => (
            <li key={page.title}>
              <span className="guide-num tabular" aria-hidden="true">
                {i + 1}
              </span>
              <span className="guide-page">
                <span className="guide-page-title">{page.title}</span>
                <span className="guide-page-note">{page.note}</span>
              </span>
            </li>
          ))}
        </ol>
      </div>
      <div className="panel-foot">
        <p className="guide-note">
          Confirm the price with the clinic before you pay.
        </p>
      </div>
    </aside>
  );
}
