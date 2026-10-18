import type { AskResponse, Citation, DebateEvent } from "./types";

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
  return (await res.json()) as AskResponse;
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
  const data = (await res.json()) as Partial<AskResponse>;
  return {
    answer: data.answer ?? "",
    citations: data.citations ?? [],
    unsupported: data.unsupported ?? [],
    trace: data.trace ?? [],
  };
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
