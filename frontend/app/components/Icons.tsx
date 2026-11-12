// Every icon is a 24px box, one stroke weight, `currentColor`. They follow the
// stroke/scale of the icons on placidway.com: 1.5, round caps, no fills.

export function Arrow({ className }: { className?: string }) {
  return (
    <svg className={`arrow ${className ?? ""}`} viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <path
        d="M2.8 8h9.4M8.4 4.2 12.2 8l-3.8 3.8"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Chevron({ open }: { open: boolean }) {
  return (
    <svg
      className={`chevron${open ? " is-open" : ""}`}
      viewBox="0 0 16 16"
      aria-hidden="true"
      focusable="false"
    >
      <path
        d="M4 6.2 8 10.2l4-4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function Thumb({ up }: { up?: boolean }) {
  return (
    <svg className="thumb" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <g transform={up ? undefined : "rotate(180 10 10)"}>
        <path
          d="M6.6 9.1 9.4 3.9a1.5 1.5 0 0 1 1.9-.7 1.5 1.5 0 0 1 .9 1.7l-.5 2.6h3.1a1.3 1.3 0 0 1 1.3 1.6l-1 4.6a1.3 1.3 0 0 1-1.3 1H6.6"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.4"
          strokeLinejoin="round"
        />
        <rect x="2.8" y="9.1" width="3.1" height="5.6" rx="0.6" fill="none" stroke="currentColor" strokeWidth="1.4" />
      </g>
    </svg>
  );
}

export function Copy({ done }: { done: boolean }) {
  if (done) {
    return (
      <svg className="copy-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
        <path
          d="M4.5 10.5 8 14l7.5-8"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.6"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
    );
  }
  return (
    <svg className="copy-icon" viewBox="0 0 20 20" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round">
        <rect x="7" y="7" width="9" height="9.5" rx="1.4" />
        <path d="M13 4.6H5.6A1.6 1.6 0 0 0 4 6.2v6.9" />
      </g>
    </svg>
  );
}

export function StopSquare() {
  return (
    <svg className="stop-icon" viewBox="0 0 16 16" aria-hidden="true" focusable="false">
      <rect x="4.5" y="4.5" width="7" height="7" rx="1.2" fill="currentColor" />
    </svg>
  );
}
