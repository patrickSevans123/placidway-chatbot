import { useMemo } from "react";
import { parseBlocks, parseInline, type Inline } from "../lib/markdown";
import type { Source } from "../lib/types";

// Citations are real links to #source-N, so they work with a keyboard and with
// JavaScript off (the card lights via :target). The click handler only adds the
// smooth scroll and the timed highlight on top of that.
export function CiteLink({
  n,
  source,
  onCite,
}: {
  n: number;
  source: Source;
  onCite: (sourceId: string) => void;
}) {
  return (
    <a
      className="cite"
      href={`#source-${source.id}`}
      aria-label={`Source ${n}: ${source.title}`}
      onClick={(event) => {
        event.preventDefault();
        onCite(source.id);
      }}
    >
      <span aria-hidden="true">{n}</span>
    </a>
  );
}

// While tokens arrive the text is plain: partial markdown re-lays itself out on
// almost every chunk, which makes the line jump under the reader's eyes.
export function StreamingText({ text }: { text: string }) {
  return (
    <div className="prose prose-stream" aria-hidden="true">
      {text.trim() ? text : null}
    </div>
  );
}

export function AnswerProse({
  markdown,
  sources,
  onCite,
}: {
  markdown: string;
  sources: Source[];
  onCite: (sourceId: string) => void;
}) {
  const blocks = useMemo(() => parseBlocks(markdown), [markdown]);
  return (
    <div className="prose">
      {blocks.map((block, i) => {
        if (block.kind === "p") {
          return (
            <p key={i}>
              <InlineParts parts={parseInline(block.text, sources.length)} sources={sources} onCite={onCite} />
            </p>
          );
        }
        const Tag = block.kind;
        return (
          <Tag key={i} className={block.kind === "ol" ? "steps" : undefined}>
            {block.items.map((item, j) => (
              <li key={j}>
                <InlineParts parts={parseInline(item, sources.length)} sources={sources} onCite={onCite} />
              </li>
            ))}
          </Tag>
        );
      })}
    </div>
  );
}

function InlineParts({
  parts,
  sources,
  onCite,
}: {
  parts: Inline[];
  sources: Source[];
  onCite: (sourceId: string) => void;
}) {
  return (
    <>
      {parts.map((part, i) => {
        if (part.kind === "bold") return <strong key={i}>{part.text}</strong>;
        if (part.kind === "cite") {
          const source = sources[part.n - 1];
          // parseInline already refuses a marker with no page behind it.
          if (!source) return null;
          return <CiteLink key={i} n={part.n} source={source} onCite={onCite} />;
        }
        return <span key={i}>{part.text}</span>;
      })}
    </>
  );
}
