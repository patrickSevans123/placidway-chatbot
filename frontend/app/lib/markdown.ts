import type { Source } from "./types";

// The answer arrives as a small subset of markdown: paragraphs, "- " or "1. "
// lists, **bold** and [n] citation markers. Everything is built as React nodes,
// so model text can never inject markup.

export type Block =
  | { kind: "p"; text: string }
  | { kind: "ul"; items: string[] }
  | { kind: "ol"; items: string[] };

const BULLET = /^\s*[-*•]\s+(.*)$/;
const NUMBER = /^\s*\d{1,2}[.)]\s+(.*)$/;

export function parseBlocks(markdown: string): Block[] {
  const lines = markdown.replace(/\r\n/g, "\n").split("\n");
  const blocks: Block[] = [];
  let paragraph: string[] | null = null;
  let list: { kind: "ul" | "ol"; items: string[] } | null = null;

  const closeParagraph = () => {
    if (paragraph) {
      const text = paragraph.join(" ").trim();
      if (text) blocks.push({ kind: "p", text });
      paragraph = null;
    }
  };
  const closeList = () => {
    if (list) blocks.push(list);
    list = null;
  };

  for (const raw of lines) {
    const line = raw.trim();
    if (!line) {
      closeParagraph();
      closeList();
      continue;
    }
    const bullet = line.match(BULLET);
    if (bullet) {
      closeParagraph();
      if (!list || list.kind !== "ul") {
        closeList();
        list = { kind: "ul", items: [] };
      }
      list.items.push(bullet[1]);
      continue;
    }
    const numbered = line.match(NUMBER);
    if (numbered) {
      closeParagraph();
      if (!list || list.kind !== "ol") {
        closeList();
        list = { kind: "ol", items: [] };
      }
      list.items.push(numbered[1]);
      continue;
    }
    closeList();
    if (!paragraph) paragraph = [];
    paragraph.push(line);
  }
  closeParagraph();
  closeList();
  return blocks;
}

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "cite"; n: number };

const INLINE = /(\*\*[^*]+\*\*)|(\[(\d{1,2})\])/g;

// A marker only becomes a link when a source with that position exists.
// Otherwise it stays as typed instead of pointing at nothing.
//
// The models write "price [1]." with a space before the marker. The marker is
// set raised, so that space shows up as a gap before the full stop. The space is
// replaced with a word joiner (U+2060) rather than deleted: no visible gap, but
// the line breaker still cannot separate the marker from the word it belongs to.
// Without it, a long answer wraps as "…to $30,000" / "1 ." on the next line.
const JOINT = "\u2060";

export function parseInline(text: string, sourceCount: number): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    const at = m.index ?? 0;
    if (at > last) out.push({ kind: "text", text: text.slice(last, at) });
    if (m[1]) {
      out.push({ kind: "bold", text: m[1].slice(2, -2) });
    } else {
      const n = Number(m[3]);
      if (n >= 1 && n <= sourceCount) {
        const before = out[out.length - 1];
        if (before && before.kind === "text") {
          const trimmed = before.text.replace(/[ \t]+$/, "");
          if (trimmed) {
            const glued = trimmed.length === before.text.length ? trimmed : trimmed + JOINT;
            out[out.length - 1] = { kind: "text", text: glued };
          } else {
            out.pop();
          }
        }
        out.push({ kind: "cite", n });
      } else {
        out.push({ kind: "text", text: m[0] });
      }
    }
    last = at + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

/** The host and path a person can read: no scheme, no www, long paths shortened at a word edge. */
export function readableUrl(url: string): string {
  try {
    const parsed = new URL(url);
    const host = parsed.hostname.replace(/^www\./, "");
    const path = decodeURIComponent(parsed.pathname).replace(/\/$/, "");
    const limit = 62;
    if (path.length <= limit) return host + path;
    const cut = path.slice(0, limit);
    const edge = Math.max(cut.lastIndexOf("/"), cut.lastIndexOf("-"));
    return host + (edge > 20 ? cut.slice(0, edge) : cut) + "…";
  } catch {
    return url;
  }
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export type { Source };
