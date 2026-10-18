"use client";

import { useEffect, useMemo, useState, type ReactNode } from "react";
import { fetchCase, fetchCases, loadMockCases } from "@/utils/api";
import {
  aggregateCases,
  caseGroup,
  GROUP_META,
  PIPELINE,
  stageChain,
  type CaseAggregate,
  type CaseGroup,
} from "@/utils/cases";
import { pct, supportTone, TONE_TEXT } from "@/utils/evidence";
import type { CaseRecord, CaseSummary } from "@/utils/types";
import { CitedText, useCitations } from "./citations";
import { Spinner } from "./debate-parts";
import { EvidenceStrip, SupportMeter } from "./evidence";
import { TraceList } from "./trace";
import { StageIcon } from "./duel";
import { EyeIcon } from "./vision";

type Source = "live" | "mock";

interface ListState {
  /** identifies the request that produced this list, so a mock/live switch triggers a reload */
  mode: boolean;
  cases: CaseSummary[];
  source: Source;
  note: string | null;
}

type RecordState = { ok: true; record: CaseRecord; note: string | null } | { ok: false; error: string };

const GROUPS: CaseGroup[] = ["success", "failure", "unreviewed"];

async function loadList(mock: boolean, signal: AbortSignal): Promise<Omit<ListState, "mode">> {
  if (mock) {
    const m = await loadMockCases();
    return { cases: m.cases, source: "mock", note: "Mock mode — synthetic example cases, not real agent runs." };
  }
  try {
    return { cases: await fetchCases(signal), source: "live", note: null };
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    const m = await loadMockCases();
    return {
      cases: m.cases,
      source: "mock",
      note: `Could not load /api/cases (${(e as Error).message.slice(0, 80)}) — showing synthetic example cases instead.`,
    };
  }
}

async function loadRecord(slug: string, source: Source, signal: AbortSignal): Promise<RecordState> {
  if (source === "mock") {
    const r = (await loadMockCases()).records[slug];
    return r ? { ok: true, record: r, note: null } : { ok: false, error: `No recorded data for “${slug}”.` };
  }
  try {
    return { ok: true, record: await fetchCase(slug, signal), note: null };
  } catch (e) {
    if ((e as Error).name === "AbortError") throw e;
    const r = (await loadMockCases().catch(() => null))?.records[slug];
    if (r) return { ok: true, record: r, note: "Backend unreachable — showing the synthetic recording of this case." };
    return { ok: false, error: (e as Error).message };
  }
}

export function CasesView({ mock, active }: { mock: boolean; active: boolean }) {
  const { register } = useCitations();
  const [list, setList] = useState<ListState | null>(null);
  const [picked, setPicked] = useState<string | null>(null);
  const [records, setRecords] = useState<Record<string, RecordState>>({});

  /* load the list the first time the tab is shown (and again if mock mode flips) */
  const listReady = list !== null && list.mode === mock;
  useEffect(() => {
    if (!active || listReady) return;
    const ctrl = new AbortController();
    loadList(mock, ctrl.signal)
      .then((l) => {
        if (ctrl.signal.aborted) return;
        setRecords({});
        setList({ ...l, mode: mock });
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [active, listReady, mock]);

  const cases = useMemo(() => (listReady ? list.cases : []), [listReady, list]);
  const grouped = useMemo(() => {
    const g: Record<CaseGroup, CaseSummary[]> = { success: [], failure: [], unreviewed: [] };
    for (const c of cases) g[caseGroup(c)].push(c);
    return g;
  }, [cases]);

  /* selection: what the user picked, else the first success / failure / anything */
  const selected =
    (picked && cases.some((c) => c.slug === picked) ? picked : null) ??
    grouped.success[0]?.slug ??
    grouped.failure[0]?.slug ??
    cases[0]?.slug ??
    null;
  const source: Source = list?.source ?? (mock ? "mock" : "live");
  const rec = selected ? records[selected] : undefined;

  useEffect(() => {
    if (!active || !selected || records[selected]) return;
    const ctrl = new AbortController();
    loadRecord(selected, source, ctrl.signal)
      .then((r) => {
        if (ctrl.signal.aborted) return;
        if (r.ok) register(r.record.citations);
        setRecords((m) => ({ ...m, [selected]: r }));
      })
      .catch(() => {});
    return () => ctrl.abort();
  }, [active, selected, source, records, register]);

  const loadingList = active && !listReady;

  return (
    <div className="space-y-6">
      {listReady && list.note && (
        <div className="animate-fade-up flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-900 ring-1 ring-amber-300">
          <span className="rounded bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-950">
            Demo
          </span>
          {list.note}
        </div>
      )}

      <section className="glass-card rounded-3xl p-5 ring-1 ring-slate-200/80 md:p-7">
        <div className="flex flex-col gap-5">
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Case files</div>
            <h2 className="text-duel-gradient text-3xl font-semibold tracking-tight">
              Where the agent wins, and where it breaks
            </h2>
            <p className="mt-1 max-w-3xl text-[14.5px] text-slate-600">
              Documented runs of the Hermes Ask agent — three successes and three failures, each annotated with the
              pipeline stage that made or broke it. Support scores come from the Nemotron reranker checking every claim
              against the passage it cites.
            </p>
          </div>
          <div className="rounded-2xl bg-slate-50/80 p-3 ring-1 ring-slate-200 md:p-4">
            <div className="mb-2 flex flex-wrap items-baseline gap-x-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
              The pipeline
              <span className="font-normal normal-case tracking-normal text-slate-400">
                where each documented case was made or broken
              </span>
            </div>
            <PipelineFlow counts={stageCounts(cases)} />
          </div>
        </div>
        <div className="mt-5">
          {loadingList ? (
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Spinner /> Loading case runs…
            </div>
          ) : (
            <MetricsTable grouped={grouped} all={cases} />
          )}
        </div>
      </section>

      {listReady && cases.length === 0 && (
        <div className="rounded-2xl bg-white p-8 text-center text-slate-600 shadow-sm ring-1 ring-slate-200">
          <p className="font-medium">No case runs recorded yet.</p>
          <p className="mt-1 text-sm text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-1.5 font-mono text-[12.5px]">
              uv run python scripts/run_cases.py
            </code>{" "}
            on the backend, then reload.
          </p>
          <button
            type="button"
            onClick={() =>
              void loadMockCases().then((m) => {
                setRecords({});
                setList({ mode: mock, cases: m.cases, source: "mock", note: "Showing synthetic example cases." });
              })
            }
            className="mt-4 rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white shadow transition hover:-translate-y-px"
          >
            Show demo cases
          </button>
        </div>
      )}

      {cases.length > 0 && (
        <div className="grid items-start gap-6 lg:grid-cols-[minmax(300px,380px)_minmax(0,1fr)]">
          <aside className="space-y-5 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:overflow-y-auto lg:pr-1 scrollbar-thin">
            {GROUPS.map((g) =>
              grouped[g].length === 0 ? null : (
                <div key={g}>
                  <h3
                    className={`mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] ${GROUP_META[g].text}`}
                  >
                    <span className={`h-2 w-2 rounded-full ${GROUP_META[g].dot}`} />
                    {GROUP_META[g].label}
                    <span className="rounded-full bg-slate-200/70 px-1.5 text-[10px] text-slate-600">
                      {grouped[g].length}
                    </span>
                  </h3>
                  <ul className="space-y-2">
                    {grouped[g].map((c) => (
                      <li key={c.slug}>
                        <CaseListItem c={c} selected={c.slug === selected} onSelect={() => setPicked(c.slug)} />
                      </li>
                    ))}
                  </ul>
                </div>
              ),
            )}
          </aside>

          <div className="min-w-0">
            {!rec ? (
              <div className="flex items-center gap-2 rounded-2xl bg-white p-8 text-sm text-slate-500 shadow-sm ring-1 ring-slate-200">
                <Spinner /> Loading case…
              </div>
            ) : rec.ok ? (
              <CaseDetail key={rec.record.slug} record={rec.record} note={rec.note} />
            ) : (
              <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-300">
                <strong>Could not load case:</strong> {rec.error}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/* ----------------------------- summary ----------------------------- */

type StageCounts = Record<string, { success: number; failure: number; unreviewed: number }>;

function stageCounts(cases: CaseSummary[]): StageCounts {
  const out: StageCounts = {};
  for (const c of cases)
    for (const m of stageChain(c.annotation?.stage ?? c.metrics.suggested_stage)) {
      const o = (out[m.key] ??= { success: 0, failure: 0, unreviewed: 0 });
      o[caseGroup(c)]++;
    }
  return out;
}

/** The five pipeline stages as a flow diagram; highlights the stage(s) that made or broke a case. */
function PipelineFlow({
  highlight,
  verdict,
  counts,
}: {
  highlight?: string | null;
  verdict?: CaseGroup;
  counts?: StageCounts;
}) {
  const chain = stageChain(highlight).map((m) => m.key);
  const hl = chain.length > 0;
  return (
    <ol className="scrollbar-thin flex items-stretch overflow-x-auto pb-1">
      {PIPELINE.map((p, i) => {
        const on = chain.includes(p.key);
        const n = counts?.[p.key];
        const node = on
          ? verdict === "failure"
            ? "bg-rose-600 text-white ring-rose-700 shadow-[0_8px_24px_-8px_rgba(225,29,72,0.8)]"
            : verdict === "success"
              ? "bg-emerald-600 text-white ring-emerald-700 shadow-[0_8px_24px_-8px_rgba(5,150,105,0.8)]"
              : "bg-slate-800 text-white ring-slate-900 shadow"
          : hl
            ? "bg-white text-slate-400 ring-slate-200"
            : p.badge;
        return (
          <li key={p.key} className="flex shrink-0 items-center">
            {i > 0 && (
              <svg viewBox="0 0 34 12" className="h-3 w-7 shrink-0 md:w-9" aria-hidden>
                <line
                  x1="0"
                  y1="6"
                  x2="27"
                  y2="6"
                  className="flow-dash"
                  stroke={on || chain.includes(PIPELINE[i - 1].key) ? "#475569" : "#94a3b8"}
                  strokeWidth="2"
                />
                <path d="M26 1.5 33 6l-7 4.5z" fill="#94a3b8" />
              </svg>
            )}
            <div
              className={`relative flex min-w-[104px] flex-col items-center gap-1 rounded-xl px-3 py-2 text-center ring-1 transition ${node} ${
                on ? "scale-105" : ""
              }`}
            >
              <span
                className={`inline-flex h-7 w-7 items-center justify-center rounded-full ${
                  on ? "bg-white/20" : hl ? "bg-slate-100" : "bg-white/70"
                }`}
              >
                <StageIcon stage={p.key} className="!h-4 !w-4" />
              </span>
              <span className="whitespace-nowrap text-[11.5px] font-semibold">{p.label}</span>
              {on && (
                <span className="whitespace-nowrap text-[10px] font-bold uppercase tracking-[0.1em] opacity-90">
                  {verdict === "failure" ? "✕ broke here" : verdict === "success" ? "✓ made it" : "involved"}
                </span>
              )}
              {n && (
                <span className="flex gap-1 text-[10px] font-semibold tabular-nums">
                  {n.success > 0 && (
                    <span className="rounded-full bg-emerald-600 px-1.5 text-white" title="successes decided here">
                      ✓ {n.success}
                    </span>
                  )}
                  {n.failure > 0 && (
                    <span className="rounded-full bg-rose-600 px-1.5 text-white" title="failures caused here">
                      ✕ {n.failure}
                    </span>
                  )}
                  {n.unreviewed > 0 && (
                    <span className="rounded-full bg-slate-500 px-1.5 text-white" title="unreviewed (heuristic guess)">
                      ? {n.unreviewed}
                    </span>
                  )}
                </span>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}

const STAMP: Record<CaseGroup, { word: string; color: string }> = {
  success: { word: "Success", color: "text-emerald-700" },
  failure: { word: "Failure", color: "text-rose-700" },
  unreviewed: { word: "Unreviewed", color: "text-slate-500" },
};

function Stamp({ group, size = "sm", rot = -8 }: { group: CaseGroup; size?: "sm" | "lg"; rot?: number }) {
  const st = STAMP[group];
  return (
    <span
      className={`rubber-stamp stamp-in ${st.color} ${size === "lg" ? "text-[22px] md:text-[28px]" : "text-[10px]"}`}
      style={{ transform: `rotate(${rot}deg)`, ["--stamp-rot" as string]: `${rot}deg` }}
    >
      {group === "success" ? "✓" : group === "failure" ? "✕" : "?"} {st.word}
    </span>
  );
}

function MetricsTable({ grouped, all }: { grouped: Record<CaseGroup, CaseSummary[]>; all: CaseSummary[] }) {
  const rows: [string, CaseAggregate, string][] = [["All runs", aggregateCases(all), "font-semibold text-slate-900"]];
  for (const g of GROUPS)
    if (grouped[g].length) rows.push([GROUP_META[g].label, aggregateCases(grouped[g]), GROUP_META[g].text]);

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[640px] border-separate border-spacing-0 text-left text-sm">
        <thead>
          <tr className="text-[10.5px] uppercase tracking-[0.12em] text-slate-500">
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold"> </th>
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Runs</th>
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold">
              Avg support <span className="normal-case tracking-normal text-slate-400">(Nemotron Rerank)</span>
            </th>
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Unsupported citations</th>
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Gold page found</th>
            <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Avg tool calls</th>
            <th className="border-b border-slate-200 py-2 font-semibold">Avg time</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([label, a, cls], i) => (
            <tr key={label} className={i === 0 ? "bg-slate-50/80" : ""}>
              <td className={`border-b border-slate-100 py-2 pl-2 pr-4 text-[13px] ${cls}`}>{label}</td>
              <td className="border-b border-slate-100 py-2 pr-4 tabular-nums text-slate-700">{a.n}</td>
              <td className="border-b border-slate-100 py-2 pr-4">
                <SupportMeter value={a.support} label="" nullLabel="no scores yet" />
              </td>
              <td className="border-b border-slate-100 py-2 pr-4 tabular-nums">
                <span className={a.nUnsupported ? "font-semibold text-red-700" : "text-emerald-700"}>
                  {pct(a.unsupportedRate)}
                </span>
                <span className="ml-1.5 text-[11px] text-slate-400">
                  {a.nUnsupported}/{a.nCited}
                </span>
              </td>
              <td className="border-b border-slate-100 py-2 pr-4 tabular-nums text-slate-700">
                {a.goldKnown ? (
                  <>
                    {pct(a.goldHit / a.goldKnown)}
                    <span className="ml-1.5 text-[11px] text-slate-400">
                      {a.goldHit}/{a.goldKnown}
                    </span>
                  </>
                ) : (
                  <span className="text-slate-400">—</span>
                )}
              </td>
              <td className="border-b border-slate-100 py-2 pr-4 tabular-nums text-slate-700">
                {a.calls === null ? "—" : a.calls.toFixed(1)}
              </td>
              <td className="border-b border-slate-100 py-2 tabular-nums text-slate-700">
                {a.duration === null ? "—" : `${a.duration.toFixed(1)} s`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* ----------------------------- list ----------------------------- */

function StageBadge({ stage, suggested = false }: { stage: string | null | undefined; suggested?: boolean }) {
  const chain = stageChain(stage);
  if (!chain.length) return null;
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[10.5px] font-semibold ring-1 ${chain[0].badge} ${
        suggested ? "opacity-70" : ""
      }`}
      title={
        suggested
          ? `Heuristic guess from the metrics — not yet reviewed (${stage})`
          : `Pipeline stage that made or broke this case: ${stage}`
      }
    >
      {suggested && <span className="font-normal italic">suggested:</span>}
      {chain.map((m) => m.label).join(" → ")}
    </span>
  );
}

function Badge({ children, tone = "slate", title }: { children: ReactNode; tone?: string; title?: string }) {
  const tones: Record<string, string> = {
    slate: "bg-slate-100 text-slate-600 ring-slate-200",
    red: "bg-red-50 text-red-700 ring-red-200",
    green: "bg-emerald-50 text-emerald-700 ring-emerald-200",
    amber: "bg-amber-50 text-amber-800 ring-amber-200",
    violet: "bg-violet-50 text-violet-800 ring-violet-200",
  };
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-md px-1.5 py-px text-[10.5px] font-semibold tabular-nums ring-1 ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function MetricBadges({ m }: { m: CaseSummary["metrics"] }) {
  const st = supportTone(m.support);
  return (
    <div className="flex flex-wrap gap-1">
      <Badge
        tone={st === "good" ? "green" : st === "mid" ? "amber" : st === "bad" ? "red" : "slate"}
        title="Mean reranker support of the answer's claims"
      >
        {m.support === null ? "support —" : `${pct(m.support)} support`}
      </Badge>
      <Badge title="Tool calls">{m.n_calls} calls</Badge>
      {!!m.n_vision_calls && (
        <Badge tone="violet" title="Calls to the vision model (inspect_page_image / compare_images)">
          <EyeIcon className="!h-3 !w-3" /> {m.n_vision_calls}
        </Badge>
      )}
      <Badge title="Citation ids used in the answer">{m.n_cited} cited</Badge>
      {m.n_unsupported > 0 && (
        <Badge tone="red" title="Cited but never retrieved">
          ⚠ {m.n_unsupported} unsupported
        </Badge>
      )}
      {m.gold_page_found !== null && (
        <Badge tone={m.gold_page_found ? "green" : "red"} title="Was the page the question is about retrieved?">
          gold page {m.gold_page_found ? "✓" : "✕"}
        </Badge>
      )}
      <Badge title="Wall-clock time">{m.duration_s.toFixed(1)} s</Badge>
    </div>
  );
}

function CaseListItem({ c, selected, onSelect }: { c: CaseSummary; selected: boolean; onSelect: () => void }) {
  const g = caseGroup(c);
  return (
    <button
      type="button"
      data-case-item
      onClick={onSelect}
      className={`index-card relative w-full rounded-md py-3 pl-9 pr-3 text-left transition duration-200 hover:-translate-y-0.5 hover:shadow-lg ${
        selected
          ? "-rotate-[0.6deg] shadow-[0_14px_30px_-12px_rgba(15,23,42,0.45)] ring-2 ring-slate-900"
          : "shadow-[0_2px_6px_-2px_rgba(15,23,42,0.2)] ring-1 ring-slate-300/70"
      }`}
    >
      <span aria-hidden className={`absolute left-2.5 top-3.5 h-2 w-2 rounded-full ${GROUP_META[g].dot}`} />
      <div className="mb-1 flex items-start gap-2">
        <code className="min-w-0 truncate pt-0.5 font-mono text-[11px] text-slate-500">{c.slug}</code>
        <span className="ml-auto shrink-0">
          <Stamp group={g} />
        </span>
      </div>
      <div className="line-clamp-2 font-serif text-[16px] font-medium leading-snug text-slate-900">{c.question}</div>
      <div className="mt-2 flex flex-wrap items-center gap-1">
        {c.annotation?.stage ? (
          <StageBadge stage={c.annotation.stage} />
        ) : (
          <StageBadge stage={c.metrics.suggested_stage} suggested />
        )}
      </div>
      <div className="mt-1.5">
        <MetricBadges m={c.metrics} />
      </div>
    </button>
  );
}

/* ----------------------------- detail ----------------------------- */

function CaseDetail({ record: r, note }: { record: CaseRecord; note: string | null }) {
  const g = caseGroup(r);
  const a = r.annotation;
  const ran = r.ran_at ? new Date(r.ran_at) : null;

  return (
    <article className="animate-fade-up pt-7">
      {/* a manila case folder: tab, typed label, rubber stamp */}
      <div className="relative">
        <span className="manila absolute -top-7 left-6 h-8 rounded-t-xl px-4 pt-1.5 font-mono text-[11px] font-semibold uppercase tracking-[0.18em] text-[#5b4128] shadow-[0_-2px_6px_-3px_rgba(90,55,20,0.35)] ring-1 ring-[#c9a46a]/60">
          Case file · {r.slug}
        </span>
      </div>
      <div className="overflow-hidden rounded-2xl bg-white shadow-lg ring-1 ring-[#c9a46a]/60">
      <header className="manila relative px-6 pb-5 pt-6 text-[#2b1d10] md:px-7">
        <div className="flex flex-col-reverse items-start gap-3 sm:flex-row sm:gap-4">
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[11px] text-[#6b4a26]">
              {r.model && <span>{r.model}</span>}
              {ran && !Number.isNaN(ran.getTime()) && <span>· {ran.toISOString().slice(0, 16).replace("T", " ")} UTC</span>}
            </div>
            <h2 className="mt-2 font-serif text-[26px] font-medium leading-snug md:text-[28px]">{r.question}</h2>
            {r.expectation && (
              <p className="mt-2 font-mono text-[12.5px] leading-relaxed text-[#4a3018]">
                <span className="mr-1.5 rounded-sm bg-[#2b1d10] px-1.5 py-px text-[10px] font-bold uppercase tracking-[0.14em] text-[#ead7ab]">
                  Expected
                </span>
                {r.expectation}
              </p>
            )}
          </div>
          <span className="shrink-0 pt-1 md:pr-2">
            <Stamp group={g} size="lg" rot={-9} />
          </span>
        </div>
      </header>

      <div className="space-y-6 px-6 py-6 md:px-7">
        {note && (
          <div className="rounded-lg bg-amber-50 px-3 py-2 text-xs text-amber-900 ring-1 ring-amber-300">{note}</div>
        )}

        {/* annotation */}
        <section className="rounded-xl bg-slate-50 p-4 ring-1 ring-slate-200">
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">Pipeline stage</span>
            {a?.stage
              ? // the raw annotation carries detail the badges drop, e.g. "Retrieval (FTS stop words)"
                a.stage.trim() !==
                  stageChain(a.stage)
                    .map((m) => m.label)
                    .join(" → ") && (
                  <span className="text-[12px] text-slate-500">
                    annotated as <em className="font-medium not-italic text-slate-700">{a.stage}</em>
                  </span>
                )
              : r.metrics.suggested_stage && (
                  <span className="text-[11px] italic text-slate-400">heuristic guess, not reviewed</span>
                )}
          </div>
          <div className="mb-4">
            <PipelineFlow highlight={a?.stage ?? r.metrics.suggested_stage} verdict={g} />
          </div>
          {a && (a.why || a.reveals) ? (
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Why</div>
                <p className="text-[14px] leading-relaxed text-slate-800">{a.why ?? "—"}</p>
              </div>
              <div>
                <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
                  What it reveals about the pipeline
                </div>
                <p className="text-[14px] leading-relaxed text-slate-800">{a.reveals ?? "—"}</p>
              </div>
            </div>
          ) : (
            <p className="text-sm italic text-slate-500">Not annotated yet.</p>
          )}
          <div className="mt-4 border-t border-slate-200 pt-3">
            <MetricBadges m={r.metrics} />
          </div>
        </section>

        {/* answer */}
        <section>
          <div className="mb-3 flex flex-wrap items-center gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Agent answer</span>
            {r.unsupported.length > 0 ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-red-300">
                ⚠ {r.unsupported.length} unsupported citation{r.unsupported.length === 1 ? "" : "s"}
              </span>
            ) : (
              r.citations.length > 0 && (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-300">
                  ✓ All citations backed by retrieved sources
                </span>
              )
            )}
          </div>
          {r.answer ? (
            <CitedText
              text={r.answer}
              citations={r.citations}
              unsupported={r.unsupported}
              className="text-[15.5px] leading-relaxed text-slate-800"
            />
          ) : (
            <p className="text-sm italic text-slate-500">No answer recorded.</p>
          )}
        </section>

        {r.evidence ? (
          <EvidenceStrip evidence={r.evidence} tone="wp" citations={r.citations} unsupported={r.unsupported} />
        ) : (
          <p className={`text-xs italic ${TONE_TEXT.none}`}>No reranker evidence recorded for this run.</p>
        )}

        {/* trace */}
        <section className="rounded-2xl bg-slate-900 px-5 py-4 text-slate-200 shadow ring-1 ring-slate-800">
          <div className="mb-3 flex items-center gap-2 text-sm font-semibold">
            Agent trace
            <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-normal">{r.trace.length} steps</span>
          </div>
          <TraceList steps={r.trace} citations={r.citations} unsupported={r.unsupported} />
        </section>
      </div>
      </div>
    </article>
  );
}
