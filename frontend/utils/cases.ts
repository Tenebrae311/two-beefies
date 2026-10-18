import { isNum } from "./evidence";
import type { CaseSummary } from "./types";

export interface StageMeta {
  key: string;
  label: string;
  badge: string;
  match: RegExp;
}

/** The pipeline, in order. Annotated case stages are matched loosely ("ocr", "Parse/OCR", "retrieval (BM25)", …). */
export const PIPELINE: StageMeta[] = [
  { key: "parse", label: "Parse/OCR", badge: "bg-orange-100 text-orange-800 ring-orange-300", match: /pars|ocr|scan/i },
  {
    key: "retrieval",
    label: "Retrieval",
    badge: "bg-sky-100 text-sky-800 ring-sky-300",
    match: /retriev|search|index|embed/i,
  },
  { key: "rerank", label: "Rerank", badge: "bg-lime-100 text-lime-800 ring-lime-300", match: /rerank/i },
  {
    key: "agent",
    label: "Agent reasoning",
    badge: "bg-violet-100 text-violet-800 ring-violet-300",
    match: /agent|reason|llm|plan|tool/i,
  },
  {
    key: "grounding",
    label: "Grounding",
    badge: "bg-emerald-100 text-emerald-800 ring-emerald-300",
    match: /ground|citat|verif/i,
  },
];

const OTHER_BADGE = "bg-slate-100 text-slate-700 ring-slate-300";

/** Best pipeline stage for one phrase: the stage whose keyword appears earliest ("Retrieval (recovered by the agent)" → Retrieval). */
function matchStage(part: string): StageMeta {
  let best: StageMeta | null = null;
  let at = Infinity;
  for (const p of PIPELINE) {
    const m = part.match(p.match);
    // "rerank" contains no retrieval keyword, but give it priority on ties anyway
    if (m && m.index !== undefined && (m.index < at || (m.index === at && p.key === "rerank"))) {
      best = p;
      at = m.index;
    }
  }
  return best ?? { key: "other", label: part.trim(), badge: OTHER_BADGE, match: /$^/ };
}

/** "Retrieval (FTS stop words) -> Agent reasoning" → [Retrieval, Agent reasoning] (the chain of stages involved). */
export function stageChain(stage: string | null | undefined): StageMeta[] {
  if (!stage?.trim()) return [];
  const out: StageMeta[] = [];
  for (const part of stage.split(/\s*(?:->|→|=>|>)\s*/)) {
    if (!part.trim()) continue;
    const m = matchStage(part);
    if (!out.some((o) => o.key === m.key)) out.push(m);
  }
  return out;
}

export function stageMeta(stage: string | null | undefined): StageMeta | null {
  return stageChain(stage)[0] ?? null;
}

export type CaseGroup = "success" | "failure" | "unreviewed";

export function caseGroup(c: CaseSummary): CaseGroup {
  const v = c.annotation?.verdict;
  return v === "success" ? "success" : v === "failure" ? "failure" : "unreviewed";
}

export const GROUP_META: Record<CaseGroup, { label: string; dot: string; text: string }> = {
  success: { label: "Successes", dot: "bg-emerald-500", text: "text-emerald-700" },
  failure: { label: "Failures", dot: "bg-rose-500", text: "text-rose-700" },
  unreviewed: { label: "Unreviewed", dot: "bg-slate-400", text: "text-slate-500" },
};

export interface CaseAggregate {
  n: number;
  support: number | null;
  unsupportedRate: number | null;
  nCited: number;
  nUnsupported: number;
  goldHit: number;
  goldKnown: number;
  calls: number | null;
  duration: number | null;
}

const mean = (xs: number[]) => (xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null);

export function aggregateCases(cs: CaseSummary[]): CaseAggregate {
  const nCited = cs.reduce((a, c) => a + (c.metrics.n_cited || 0), 0);
  const nUnsupported = cs.reduce((a, c) => a + (c.metrics.n_unsupported || 0), 0);
  const gold = cs.map((c) => c.metrics.gold_page_found).filter((g): g is boolean => typeof g === "boolean");
  return {
    n: cs.length,
    support: mean(cs.map((c) => c.metrics.support).filter(isNum)),
    // n_cited already includes the unsupported (cited-but-never-retrieved) ids
    unsupportedRate: nCited > 0 ? nUnsupported / nCited : null,
    nCited,
    nUnsupported,
    goldHit: gold.filter(Boolean).length,
    goldKnown: gold.length,
    calls: mean(cs.map((c) => c.metrics.n_calls).filter(isNum)),
    duration: mean(cs.map((c) => c.metrics.duration_s).filter(isNum)),
  };
}
