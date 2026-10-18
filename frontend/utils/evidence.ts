import type { Anachronism, ClaimFlag, Evidence, EvidenceClaim, Role, VerdictEvidence } from "./types";

export const RERANK_LABEL = "Nemotron Rerank";

export const FLAG_META: Record<ClaimFlag, { label: string; explain: string; dot: string; row: string; score: string }> =
  {
    supported: {
      label: "Supported",
      explain: "Its cited passage backs the claim",
      dot: "bg-emerald-500",
      row: "",
      score: "text-emerald-700",
    },
    weak: {
      label: "Weak",
      explain: "The cited passage only partly backs it",
      dot: "bg-amber-400",
      row: "",
      score: "text-amber-700",
    },
    unsupported: {
      label: "Unsupported",
      explain: "The cited passage does not back it",
      dot: "bg-rose-500",
      row: "bg-rose-50/80 ring-1 ring-rose-200",
      score: "text-rose-700",
    },
    uncited: {
      label: "Uncited",
      explain: "No citation was given for this claim",
      dot: "bg-slate-400",
      row: "",
      score: "text-slate-500",
    },
    anachronism: {
      label: "Anachronism",
      explain: "Not in his own 18th/19th-century sources, but supported by modern Wikipedia",
      dot: "bg-red-600",
      row: "bg-gradient-to-r from-red-100/90 via-red-50 to-amber-50 ring-1 ring-red-400 shadow-sm",
      score: "text-red-700",
    },
  };

export const FLAG_ORDER: ClaimFlag[] = ["supported", "weak", "unsupported", "uncited", "anachronism"];

export function normalizeFlag(f: string | undefined): ClaimFlag {
  const k = String(f ?? "")
    .toLowerCase()
    .trim();
  if (k in FLAG_META) return k as ClaimFlag;
  if (k.startsWith("anachron")) return "anachronism";
  if (k.startsWith("unsup")) return "unsupported";
  if (k.startsWith("uncit") || k.startsWith("no_cit")) return "uncited";
  if (k.startsWith("weak") || k.startsWith("partial")) return "weak";
  return "supported";
}

export function isNum(v: unknown): v is number {
  return typeof v === "number" && Number.isFinite(v);
}

/** 0..1 → "73%"; null → "—" */
export function pct(v: number | null | undefined): string {
  return isNum(v) ? `${Math.round(Math.max(0, Math.min(1, v)) * 100)}%` : "—";
}

export type SupportTone = "good" | "mid" | "bad" | "none";

export function supportTone(v: number | null | undefined): SupportTone {
  if (!isNum(v)) return "none";
  if (v >= 0.6) return "good";
  if (v >= 0.35) return "mid";
  return "bad";
}

export const TONE_BAR: Record<SupportTone, string> = {
  good: "bg-emerald-500",
  mid: "bg-amber-400",
  bad: "bg-rose-500",
  none: "bg-slate-300",
};

export const TONE_TEXT: Record<SupportTone, string> = {
  good: "text-emerald-700",
  mid: "text-amber-700",
  bad: "text-rose-700",
  none: "text-slate-500",
};

/** Defensive normalisation of an evidence payload coming off the wire. */
export function normalizeEvidence(e: Partial<Evidence> | null | undefined): Evidence | null {
  if (!e) return null;
  const claims: EvidenceClaim[] = (Array.isArray(e.claims) ? e.claims : []).map((c) => ({
    text: String(c?.text ?? ""),
    cites: Array.isArray(c?.cites) ? c.cites.map(String) : [],
    support: isNum(c?.support) ? c.support : null,
    modern_support: isNum(c?.modern_support) ? c.modern_support : null,
    flag: normalizeFlag(c?.flag),
  }));
  return { support: isNum(e.support) ? e.support : null, claims };
}

function mean(xs: number[]): number | null {
  return xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null;
}

/** Fallback for a verdict without `evidence`: aggregate what the per-turn evidence events reported. */
export function summarizeTurnEvidence(
  turns: { role: Role; round: number; evidence?: Evidence | null }[],
): VerdictEvidence | null {
  const scored = turns.filter((t) => t.evidence);
  if (!scored.length) return null;
  const sideMean = (role: Role) =>
    mean(scored.filter((t) => t.role === role && isNum(t.evidence!.support)).map((t) => t.evidence!.support as number));
  const anachronisms: Anachronism[] = [];
  for (const t of scored) {
    if (t.role !== "britannica") continue;
    for (const c of t.evidence!.claims) {
      if (c.flag === "anachronism")
        anachronisms.push({
          round: t.round,
          text: c.text,
          support: c.support,
          modern_support: c.modern_support ?? null,
        });
    }
  }
  return { britannica: sideMean("britannica"), wikipedia: sideMean("wikipedia"), anachronisms };
}
