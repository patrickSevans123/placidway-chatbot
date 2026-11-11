// Every icon is a 24px box, one stroke weight, `currentColor`. They follow the
// stroke/scale of the icons on placidway.com: 1.5, round caps, no fills.

import type { Starter } from "../lib/brand";

type IconName = Starter["icon"];

const PATHS: Record<IconName, React.ReactNode> = {
  price: (
    <>
      <path d="M3.5 12.2 12 3.7h7.5v7.5l-8.5 8.5z" />
      <circle cx="15.8" cy="8.2" r="1.4" />
    </>
  ),
  list: (
    <>
      <path d="M9.5 6.5h11M9.5 12h11M9.5 17.5h11" />
      <path d="M4.4 6.5 5.6 7.7l2-2.4M4.4 12l1.2 1.2 2-2.4M4.4 17.5l1.2 1.2 2-2.4" />
    </>
  ),
  doctor: (
    <>
      <circle cx="12" cy="8" r="3.6" />
      <path d="M5 20.5a7 7 0 0 1 14 0" />
      <path d="M11 5.6h2" />
    </>
  ),
  route: (
    <>
      <circle cx="6" cy="6" r="2.5" />
      <circle cx="18" cy="18" r="2.5" />
      <path d="M8.5 6h5.5a4 4 0 0 1 0 8H10a4 4 0 0 0 0 8" />
    </>
  ),
  review: (
    <>
      <path d="M12 3.8l2.5 5.1 5.6.8-4.05 3.95.96 5.58L12 16.6l-5.01 2.63.96-5.58L3.9 9.7l5.6-.8z" />
    </>
  ),
  video: (
    <>
      <rect x="3.2" y="6" width="12.4" height="12" rx="2" />
      <path d="M15.6 10.4 20.5 7.6v8.8l-4.9-2.8z" />
    </>
  ),
};

export function Icon({ name }: { name: IconName }) {
  return (
    <svg className="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <g fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        {PATHS[name]}
      </g>
    </svg>
  );
}

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
