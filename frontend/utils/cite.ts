import { bareId } from "./api";
import type { Citation, PointCategory, VerdictPoint } from "./types";

export type Segment = { kind: "text"; text: string } | { kind: "cite"; id: string };

// Matches [EB:abc], [WP:Foo_Bar], [EB:a, EB:b], [EB:a; WP:b]
const CITE_RE = /\[\s*((?:EB|WP)\s*:[^[\]\n]+?)\s*\]/gi;

export function splitCitations(text: string): Segment[] {
  const out: Segment[] = [];
  let last = 0;
  for (const m of text.matchAll(CITE_RE)) {
    const idx = m.index ?? 0;
    if (idx > last) out.push({ kind: "text", text: text.slice(last, idx) });
    let prefix = "";
    for (const rawPiece of m[1].split(/[,;]\s*/)) {
      const piece = rawPiece.trim();
      if (!piece) continue;
      const pm = piece.match(/^(EB|WP)\s*:\s*(.+)$/i);
      if (pm) {
        prefix = pm[1].toUpperCase();
        out.push({ kind: "cite", id: `${prefix}:${pm[2].trim()}` });
      } else if (prefix) {
        out.push({ kind: "cite", id: `${prefix}:${piece}` });
      }
    }
    last = idx + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

export function sameId(a: string, b: string): boolean {
  return a === b || bareId(a) === bareId(b);
}

export function findCitation(id: string, ...lists: (Citation[] | undefined)[]): Citation | undefined {
  for (const list of lists) {
    if (!list) continue;
    const hit = list.find((c) => sameId(c.cite_id, id));
    if (hit) return hit;
  }
  return undefined;
}

export function isUnsupported(id: string, unsupported: string[] | undefined): boolean {
  return !!unsupported?.some((u) => sameId(u, id));
}

/** Moderator turn text may be JSON (possibly fenced). Extract what we can. */
export interface ModeratorRuling {
  summary?: string;
  points?: VerdictPoint[];
  converged?: boolean;
}

export function parseModerator(text: string): ModeratorRuling | null {
  if (!text) return null;
  let t = text.trim();
  const fence = t.match(/```(?:json)?\s*([\s\S]*?)```/i);
  if (fence) t = fence[1].trim();
  if (!t.startsWith("{")) {
    const s = t.indexOf("{");
    const e = t.lastIndexOf("}");
    if (s === -1 || e <= s) return null;
    t = t.slice(s, e + 1);
  }
  try {
    const obj = JSON.parse(t) as Record<string, unknown>;
    const summary =
      (obj.summary as string) ?? (obj.round_summary as string) ?? (obj.assessment as string) ?? (obj.text as string);
    const points = Array.isArray(obj.points) ? (obj.points as VerdictPoint[]) : undefined;
    const converged = typeof obj.converged === "boolean" ? obj.converged : undefined;
    return { summary, points, converged };
  } catch {
    return null;
  }
}

export const CATEGORY_META: Record<
  PointCategory,
  { label: string; short: string; explain: string; badge: string; dot: string }
> = {
  language: {
    label: "Language",
    short: "language",
    explain: "Same fact, different words",
    badge: "bg-sky-100 text-sky-800 ring-sky-300",
    dot: "bg-sky-500",
  },
  knowledge: {
    label: "Knowledge",
    short: "knowledge",
    explain: "The facts themselves changed",
    badge: "bg-amber-100 text-amber-900 ring-amber-300",
    dot: "bg-amber-500",
  },
  perspective: {
    label: "Perspective",
    short: "perspective",
    explain: "Values or framing changed",
    badge: "bg-violet-100 text-violet-800 ring-violet-300",
    dot: "bg-violet-500",
  },
  no_counterpart: {
    label: "No counterpart",
    short: "no counterpart",
    explain: "No modern equivalent found",
    badge: "bg-slate-200 text-slate-700 ring-slate-300",
    dot: "bg-slate-500",
  },
};

export function normalizeCategory(c: string | undefined): PointCategory {
  const k = (c ?? "").toLowerCase().trim().replace(/[\s-]+/g, "_");
  if (k in CATEGORY_META) return k as PointCategory;
  if (k.startsWith("no")) return "no_counterpart";
  if (k.startsWith("lang")) return "language";
  if (k.startsWith("persp")) return "perspective";
  return "knowledge";
}

export function categoryMeta(c: string | undefined) {
  return CATEGORY_META[normalizeCategory(c)];
}

export function agreementOf(points: VerdictPoint[] | undefined): { pct: number; agreed: number; total: number } | null {
  if (!points || points.length === 0) return null;
  const agreed = points.filter((p) => isAgreed(p.status)).length;
  return { pct: Math.round((agreed / points.length) * 100), agreed, total: points.length };
}

export function isAgreed(status: string | undefined): boolean {
  return String(status ?? "").toLowerCase().startsWith("agree");
}
