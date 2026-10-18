import { normalizeEvidence } from "./evidence";
import type { AskResponse, CaseMetrics, CaseRecord, CaseSummary, Citation, DebateEvent, TraceStep } from "./types";
import { normalizeVision } from "./vision";

/** Direct backend URL — used for the SSE stream (Next rewrites may buffer SSE). */
export const BACKEND_URL = (process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8000").replace(/\/$/, "");

export function isMockRequested(): boolean {
  if (typeof window === "undefined") return false;
  const v = new URLSearchParams(window.location.search).get("mock");
  return v === "1" || v === "true";
}

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Strip the "EB:" / "WP:" prefix so ids can be matched in either form. */
export function bareId(id: string): string {
  return id.replace(/^(EB|WP)\s*:\s*/i, "").trim();
}

export function sourceFromId(id: string): Citation["source"] | null {
  if (/^EB\s*:/i.test(id)) return "britannica";
  if (/^WP\s*:/i.test(id)) return "wikipedia";
  return null;
}

let mockDebateCache: DebateEvent[] | null = null;
export async function loadMockDebate(): Promise<DebateEvent[]> {
  if (mockDebateCache) return mockDebateCache;
  const res = await fetch("/mock-debate.json");
  mockDebateCache = (await res.json()) as DebateEvent[];
  return mockDebateCache;
}

export async function loadMockAsk(): Promise<AskResponse> {
  const res = await fetch("/mock-ask.json");
  return normalizeAsk((await res.json()) as Partial<AskResponse>);
}

function normalizeTrace(trace: Partial<TraceStep>[] | undefined): TraceStep[] {
  return (trace ?? []).map((t) => ({
    name: String(t.name ?? "tool"),
    args: t.args ?? {},
    n_hits: typeof t.n_hits === "number" ? t.n_hits : undefined,
    cite_ids: Array.isArray(t.cite_ids) ? t.cite_ids : undefined,
    vision: normalizeVision(t.vision),
  }));
}

function normalizeAsk(data: Partial<AskResponse>): AskResponse {
  return {
    answer: data.answer ?? "",
    citations: data.citations ?? [],
    unsupported: data.unsupported ?? [],
    trace: normalizeTrace(data.trace),
    evidence: normalizeEvidence(data.evidence),
  };
}

/** POST /api/ask through the Next rewrite. Throws on network / 5xx so callers can fall back to mock. */
export async function askBackend(question: string, signal?: AbortSignal): Promise<AskResponse> {
  const res = await fetch("/api/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
    signal,
  });
  if (!res.ok) {
    let detail = "";
    try {
      detail = await res.text();
    } catch {}
    const err = new Error(`Backend responded ${res.status}${detail ? `: ${detail.slice(0, 200)}` : ""}`);
    (err as Error & { status?: number }).status = res.status;
    throw err;
  }
  return normalizeAsk((await res.json()) as Partial<AskResponse>);
}

/* ------------------------------ documented cases ------------------------------ */

export interface MockCases {
  cases: CaseSummary[];
  records: Record<string, CaseRecord>;
}

function normalizeMetrics(m: Partial<CaseMetrics> | undefined): CaseMetrics {
  return {
    duration_s: Number(m?.duration_s ?? 0),
    n_calls: Number(m?.n_calls ?? 0),
    n_cited: Number(m?.n_cited ?? 0),
    n_unsupported: Number(m?.n_unsupported ?? 0),
    support: typeof m?.support === "number" ? m.support : null,
    gold_page_found: typeof m?.gold_page_found === "boolean" ? m.gold_page_found : null,
    n_vision_calls: typeof m?.n_vision_calls === "number" ? m.n_vision_calls : undefined,
    n_weak_claims: typeof m?.n_weak_claims === "number" ? m.n_weak_claims : undefined,
    suggested_stage: m?.suggested_stage ?? null,
  };
}

function normalizeCaseSummary(c: Partial<CaseSummary>): CaseSummary {
  return {
    slug: String(c.slug ?? ""),
    question: c.question ?? "",
    expectation: c.expectation ?? "",
    annotation: c.annotation ?? null,
    metrics: normalizeMetrics(c.metrics),
  };
}

function normalizeCaseRecord(c: Partial<CaseRecord>): CaseRecord {
  return {
    ...normalizeCaseSummary(c),
    answer: c.answer ?? "",
    citations: c.citations ?? [],
    unsupported: c.unsupported ?? [],
    trace: normalizeTrace(c.trace),
    evidence: normalizeEvidence(c.evidence),
    ran_at: c.ran_at ?? "",
    model: c.model ?? "",
  };
}

let mockCasesCache: MockCases | null = null;
export async function loadMockCases(): Promise<MockCases> {
  if (mockCasesCache) return mockCasesCache;
  const res = await fetch("/mock-cases.json");
  const raw = (await res.json()) as { cases?: Partial<CaseSummary>[]; records?: Record<string, Partial<CaseRecord>> };
  const cases = (raw.cases ?? []).map(normalizeCaseSummary);
  const records: Record<string, CaseRecord> = {};
  // per-slug records only carry the detail fields; question / metrics / annotation come from the summary
  for (const [slug, r] of Object.entries(raw.records ?? {}))
    records[slug] = normalizeCaseRecord({ ...cases.find((c) => c.slug === slug), slug, ...r });
  mockCasesCache = { cases, records };
  return mockCasesCache;
}

/** GET /api/cases through the Next rewrite. Throws on any failure so callers can fall back to mock. */
export async function fetchCases(signal?: AbortSignal): Promise<CaseSummary[]> {
  const res = await fetch("/api/cases", { signal });
  if (!res.ok) throw new Error(`Backend responded ${res.status}`);
  const data = (await res.json()) as unknown;
  if (!Array.isArray(data)) throw new Error("Unexpected /api/cases payload");
  return (data as Partial<CaseSummary>[]).map(normalizeCaseSummary);
}

export async function fetchCase(slug: string, signal?: AbortSignal): Promise<CaseRecord> {
  const res = await fetch(`/api/cases/${encodeURIComponent(slug)}`, { signal });
  if (!res.ok) throw new Error(`Backend responded ${res.status}`);
  return normalizeCaseRecord((await res.json()) as Partial<CaseRecord>);
}

export async function fetchSource(citeId: string, signal?: AbortSignal): Promise<Citation | null> {
  try {
    const res = await fetch(`/api/source/${encodeURIComponent(citeId)}`, { signal });
    if (!res.ok) return null;
    return (await res.json()) as Citation;
  } catch {
    return null;
  }
}

export function formatArgs(args: Record<string, unknown> | undefined): string {
  if (!args) return "";
  const vals = Object.values(args);
  if (vals.length === 1 && typeof vals[0] === "string") return `'${vals[0]}'`;
  return Object.entries(args)
    .map(([k, v]) => `${k}=${typeof v === "string" ? `'${v}'` : JSON.stringify(v)}`)
    .join(", ");
}

let mockSourcesCache: Record<string, Citation> | null = null;
/** Full-text lookup for mock mode (public/mock-sources.json). */
export async function fetchMockSource(citeId: string): Promise<Citation | null> {
  try {
    if (!mockSourcesCache) {
      const res = await fetch("/mock-sources.json");
      mockSourcesCache = (await res.json()) as Record<string, Citation>;
    }
    const all = Object.values(mockSourcesCache);
    return mockSourcesCache[citeId] ?? all.find((c) => bareId(c.cite_id) === bareId(citeId)) ?? null;
  } catch {
    return null;
  }
}
