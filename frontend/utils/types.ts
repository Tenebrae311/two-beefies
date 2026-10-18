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

export interface Verdict {
  converged: boolean;
  points: VerdictPoint[];
  summary: string;
}

export type DebateEvent =
  | { type: "turn_start"; role: Role; round: number }
  | { type: "token"; role: Role; text: string }
  | { type: "tool_call"; role: Role; name: string; args: Record<string, unknown> }
  | { type: "tool_result"; role: Role; name: string; hits: Citation[] }
  | {
      type: "turn_end";
      role: Role;
      round: number;
      text: string;
      citations?: Citation[];
      unsupported?: string[];
    }
  | ({ type: "verdict" } & Verdict)
  | { type: "done" }
  | { type: "error"; message: string };

export interface TraceStep {
  name: string;
  args: Record<string, unknown>;
}

export interface AskResponse {
  answer: string;
  citations: Citation[];
  unsupported: string[];
  trace: TraceStep[];
}
