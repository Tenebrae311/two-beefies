export type Source = "britannica" | "wikipedia";
export type Role = "britannica" | "wikipedia" | "moderator";

export interface Citation {
  cite_id: string;
  source: Source;
  title: string;
  snippet: string;
  url: string;
  image_url?: string | null;
  edition?: string | null;
  year?: number | null;
  text?: string;
}

export type PointStatus = "agreed" | "disputed";
export type PointCategory = "language" | "knowledge" | "perspective" | "no_counterpart";

export interface VerdictPoint {
  claim: string;
  britannica?: string;
  wikipedia?: string;
  status: PointStatus;
  category: PointCategory;
  cites?: string[];
}

/* ---------------- evidence (Nemotron Rerank as a fact-checker) ---------------- */

export type ClaimFlag = "supported" | "weak" | "unsupported" | "uncited" | "anachronism";

export interface EvidenceClaim {
  text: string;
  cites: string[];
  /** 0..1: how strongly the claim's own cited passages support it (null = not scorable / reranker offline) */
  support: number | null;
  /** Britannica claims only: how strongly modern Wikipedia supports the same claim */
  modern_support?: number | null;
  flag: ClaimFlag;
}

export interface Evidence {
  /** 0..1 mean support of the claims by their own cited sources; null if the reranker is unavailable */
  support: number | null;
  claims: EvidenceClaim[];
}

export interface Anachronism {
  round: number;
  text: string;
  support: number | null;
  modern_support: number | null;
}

export interface VerdictEvidence {
  britannica: number | null;
  wikipedia: number | null;
  anachronisms: Anachronism[];
}

export interface Verdict {
  converged: boolean;
  points: VerdictPoint[];
  summary: string;
  evidence?: VerdictEvidence | null;
}

/* ---------------- vision (Nemotron VL looking at the actual scan) ---------------- */

export interface VisionResult {
  question: string;
  answer: string;
  /** "/api/page-image/<n>" (relative, via the Next rewrite) and/or absolute Wikipedia image URLs */
  images: string[];
}

export type DebateEvent =
  | { type: "turn_start"; role: Role; round: number }
  | { type: "token"; role: Role; text: string }
  | { type: "tool_call"; role: Role; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; role: Role; name: string; hits: Citation[]; vision?: VisionResult | null }
  | {
      type: "turn_end";
      role: Role;
      round: number;
      text: string;
      citations?: Citation[];
      unsupported?: string[];
    }
  | {
      type: "evidence";
      role: "britannica" | "wikipedia";
      round: number;
      support: number | null;
      claims: EvidenceClaim[];
    }
  | ({ type: "verdict" } & Verdict)
  | { type: "done" }
  | { type: "error"; message: string };

export interface TraceStep {
  name: string;
  args: Record<string, unknown>;
  n_hits?: number;
  cite_ids?: string[];
  vision?: VisionResult | null;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  unsupported: string[];
  trace: TraceStep[];
  evidence?: Evidence | null;
}

/* ---------------- documented agent cases (/api/cases) ---------------- */

export type CaseVerdict = "success" | "failure";

export interface CaseAnnotation {
  verdict: CaseVerdict | null;
  /** pipeline stage that made or broke the case, e.g. "Parse/OCR", "Retrieval", "Rerank", "Agent reasoning", "Grounding" */
  stage: string | null;
  why: string | null;
  reveals: string | null;
}

export interface CaseMetrics {
  duration_s: number;
  n_calls: number;
  /** all cited ids, including the unsupported ones */
  n_cited: number;
  n_unsupported: number;
  support: number | null;
  gold_page_found: boolean | null;
  n_vision_calls?: number;
  n_weak_claims?: number;
  /** heuristic first guess at the failing stage (scripts/run_cases.py); the annotation has the final word */
  suggested_stage?: string | null;
}

export interface CaseSummary {
  slug: string;
  question: string;
  expectation: string;
  annotation: CaseAnnotation | null;
  metrics: CaseMetrics;
}

export interface CaseRecord extends CaseSummary {
  answer: string;
  citations: Citation[];
  unsupported: string[];
  trace: TraceStep[];
  evidence: Evidence | null;
  ran_at: string;
  model: string;
}
