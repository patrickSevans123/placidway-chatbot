// The bar is the page's one fixed object: their mark at its real 2:1 box
// (104x52 in a 64px bar), the words that name the guide, and one action. The
// action appears only once there is a conversation to leave, so the empty screen
// asks for a question and nothing else.
export function Header({ onNew }: { onNew?: () => void }) {
  return (
    <header className="top" data-conv={onNew ? "true" : undefined}>
      <div className="top-inner">
        <a className="brand" href="./" aria-label="PlacidWay treatment guide, start again">
          <img
            className="brand-logo"
            src="/placidway-logo.png"
            srcSet="/placidway-logo.png 1x, /placidway-logo@2x.png 2x"
            width={104}
            height={52}
            alt="PlacidWay"
            fetchPriority="high"
            decoding="async"
          />
          <span className="brand-sub">Treatment guide</span>
        </a>

        {onNew && (
          <button type="button" className="top-new" onClick={onNew}>
            <span className="top-new-plus" aria-hidden="true">
              +
            </span>
            New conversation
          </button>
        )}
      </div>
    </header>
  );
}
