"use client";

import { formatArgs } from "@/utils/api";
import { agreementOf, CATEGORY_META, categoryMeta, isAgreed, normalizeCategory, parseModerator } from "@/utils/cite";
import { isNum, pct as pctOf } from "@/utils/evidence";
import type { ToolActivity, Turn } from "@/utils/useDebate";
import type { PointCategory, Verdict, VerdictEvidence, VerdictPoint } from "@/utils/types";
import { isVisionTool } from "@/utils/vision";
import { CitationChip, CitedText } from "./citations";
import { BalanceScale, CategoryIcon, WaxSeal } from "./duel";
import { EvidenceStrip, HourglassIcon, VerdictEvidencePanel } from "./evidence";
import { EyeIcon, VisionCard } from "./vision";

/* ----------------------------- small atoms ----------------------------- */

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent ${className}`}
    />
  );
}

export function SearchIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-3.5 w-3.5 fill-current ${className}`} aria-hidden>
      <path d="M8.5 2a6.5 6.5 0 0 1 5.18 10.43l3.45 3.45a1 1 0 0 1-1.41 1.41l-3.45-3.45A6.5 6.5 0 1 1 8.5 2Zm0 2a4.5 4.5 0 1 0 0 9 4.5 4.5 0 0 0 0-9Z" />
    </svg>
  );
}

export function StatusBadge({ status }: { status: VerdictPoint["status"] }) {
  const agreed = isAgreed(status);
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${
        agreed ? "bg-emerald-50 text-emerald-700 ring-emerald-300" : "bg-rose-50 text-rose-700 ring-rose-300"
      }`}
    >
      {agreed ? "✓ Agreed" : "✕ Disputed"}
    </span>
  );
}

export function CategoryBadge({ category }: { category: PointCategory | string }) {
  const m = categoryMeta(category);
  return (
    <span
      className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full py-0.5 pl-1.5 pr-2 text-[11px] font-semibold ring-1 ${m.badge}`}
      title={m.explain}
    >
      <CategoryIcon category={normalizeCategory(category)} className="!h-3 !w-3" />
      {m.label}
    </span>
  );
}

const CATEGORY_TILE: Record<PointCategory, string> = {
  language: "bg-sky-600",
  knowledge: "bg-amber-500",
  perspective: "bg-violet-600",
  no_counterpart: "bg-slate-500",
};

/** The four kinds of change, as small icon tiles. */
export function CategoryLegend() {
  return (
    <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-4">
      {(Object.keys(CATEGORY_META) as PointCategory[]).map((k) => (
        <div key={k} className="flex items-center gap-3 rounded-xl bg-white px-3 py-2 ring-1 ring-slate-200">
          <span
            className={`inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-lg text-white shadow-sm ${CATEGORY_TILE[k]}`}
          >
            <CategoryIcon category={k} className="!h-4 !w-4" />
          </span>
          <span className="min-w-0">
            <span className="block text-[13px] font-semibold text-slate-900">{CATEGORY_META[k].label}</span>
            <span className="block text-[12px] leading-snug text-slate-600">{CATEGORY_META[k].explain}</span>
          </span>
        </div>
      ))}
    </div>
  );
}

/* ----------------------------- tool activity ----------------------------- */

const TOOL_VERBS: Record<string, [pending: string, done: string]> = {
  search_britannica: ["Searching the archives", "Searched the archives"],
  get_britannica_page: ["Fetching the page", "Read the page"],
  search_wikipedia: ["Querying Wikipedia", "Queried Wikipedia"],
  get_wikipedia_article: ["Opening the article", "Read the article"],
  inspect_page_image: ["Examining the scan", "Examined the scan"],
  compare_images: ["Comparing the images", "Compared the images"],
};

function toolVerb(name: string, done: boolean, eb: boolean): string {
  const v = TOOL_VERBS[name];
  if (v) return done ? v[1] : v[0];
  if (done) return name.replace(/_/g, " ");
  return eb ? "Consulting the archives" : "Searching";
}

export function ToolPill({ tool, tone }: { tool: ToolActivity; tone: "eb" | "wp" }) {
  const vision = isVisionTool(tool.name);
  const eb = tone === "eb";
  const base = vision
    ? "bg-violet-50 text-violet-950 ring-violet-300"
    : eb
      ? "bg-[#f3e2bb] text-[#4a2a0c] ring-[#c9a46a]"
      : "bg-sky-50 text-sky-950 ring-sky-200";
  const dot = vision ? "bg-violet-600 text-white" : eb ? "bg-[#7a2e12] text-amber-50" : "bg-slate-900 text-white";
  const args = formatArgs(tool.args);
  return (
    <div
      title={`${tool.name}(${args})`}
      className={`animate-fade-up inline-flex max-w-full items-center gap-1.5 rounded-full py-0.5 pl-0.5 pr-2.5 ring-1 ${base} ${
        tool.done ? "" : "pill-live shadow-sm"
      }`}
    >
      <span className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${dot}`}>
        {!tool.done ? (
          <Spinner className="!h-2.5 !w-2.5" />
        ) : vision ? (
          <EyeIcon className="!h-3 !w-3" />
        ) : (
          <SearchIcon className="!h-3 !w-3" />
        )}
      </span>
      <span className={`shrink-0 text-[11.5px] font-semibold ${eb && !vision ? "font-fell text-[13px] italic" : ""}`}>
        {toolVerb(tool.name, tool.done, eb)}
        {!tool.done && <span className="dots" />}
      </span>
      {args && <span className="min-w-0 truncate font-mono text-[10.5px] opacity-70">{args}</span>}
      {tool.done && (
        <span className="ml-0.5 shrink-0 rounded-full bg-black/[0.07] px-1.5 text-[10.5px] font-semibold tabular-nums">
          {vision ? "seen" : `${tool.hits?.length ?? 0} hit${tool.hits?.length === 1 ? "" : "s"}`}
        </span>
      )}
    </div>
  );
}

/* ----------------------------- turn bubbles ----------------------------- */

export function TurnBubble({ turn, awaitingEvidence = false }: { turn: Turn; awaitingEvidence?: boolean }) {
  const eb = turn.role === "britannica";
  const streaming = !turn.finished;
  const pendingTool = turn.tools.findLast((t) => !t.done);
  const searching = !!pendingTool;
  const badCount = turn.unsupported.length;
  const looked = turn.tools.filter((t) => t.vision);

  return (
    <div className={eb ? "animate-in-left" : "animate-in-right"}>
      <article
        className={`relative rounded-2xl p-5 transition-shadow md:p-6 ${
          eb
            ? "border border-[#cfae74] bg-[#fbf3df] text-ink shadow-[0_10px_28px_-14px_rgba(90,55,20,0.55),inset_0_0_0_4px_#fbf3df,inset_0_0_0_5px_rgba(201,164,106,0.45)]"
            : "overflow-hidden border border-slate-200 bg-white text-slate-800 shadow-[0_10px_28px_-16px_rgba(15,23,42,0.4)]"
        } ${streaming ? (eb ? "ring-2 ring-[#c9a46a]/60" : "ring-2 ring-sky-300/60") : ""}`}
      >
        {!eb && (
          <span aria-hidden className="absolute inset-x-0 top-0 h-1 bg-gradient-to-r from-sky-400 via-indigo-400 to-violet-400" />
        )}
        <header className="mb-3 flex items-center justify-between gap-2">
          {eb ? (
            <span className="font-fell text-[16px] italic text-[#7a2e12]">
              <span aria-hidden className="mr-1.5 not-italic opacity-70">
                ❦
              </span>
              The {ordinal(turn.round)} Round
            </span>
          ) : (
            <span className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
              Round {turn.round} · Editor
              <span className="rounded bg-slate-100 px-1.5 py-px font-mono text-[10px] normal-case tracking-normal text-slate-500 ring-1 ring-slate-200">
                rev. 2026
              </span>
            </span>
          )}
          {streaming && (
            <span className={`inline-flex items-center gap-1.5 text-[11px] font-medium ${eb ? "text-[#7a5230]" : "text-sky-700"}`}>
              <Spinner />
              <span className="dots">
                {pendingTool && isVisionTool(pendingTool.name)
                  ? "examining the scan"
                  : searching
                    ? eb
                      ? "searching the archives"
                      : "querying Wikipedia"
                    : eb
                      ? "the quill moves"
                      : "typing"}
              </span>
            </span>
          )}
        </header>
        {eb && <div aria-hidden className="engraved-rule -mt-1 mb-3" />}

        {turn.tools.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-1.5">
            {turn.tools.map((t, i) => (
              <ToolPill key={i} tool={t} tone={eb ? "eb" : "wp"} />
            ))}
          </div>
        )}

        {looked.length > 0 && (
          <div className="mb-3 space-y-2">
            {looked.map((t, i) => (
              <VisionCard key={i} name={t.name} args={t.args} vision={t.vision!} tone={eb ? "eb" : "wp"} />
            ))}
          </div>
        )}

        {turn.text ? (
          <CitedText
            text={turn.text}
            citations={turn.citations}
            unsupported={turn.unsupported}
            streaming={streaming}
            dropCap={eb}
            className={eb ? "font-serif text-[17.5px] leading-[1.55]" : "text-[15px] leading-relaxed"}
          />
        ) : (
          streaming &&
          !searching && (
            <p className={`text-sm italic opacity-60 ${eb ? "font-serif" : ""}`}>
              {eb ? "The scholar dips his quill…" : "Drafting a reply…"}
            </p>
          )
        )}

        {turn.finished && (turn.citations.length > 0 || badCount > 0) && (
          <footer
            className={`mt-4 flex flex-wrap items-center gap-2 border-t pt-3 text-[11px] ${
              eb ? "border-[#e2cd9f] font-fell text-[13px] italic text-[#7a5230]" : "border-slate-100 text-slate-500"
            }`}
          >
            <span>
              {turn.citations.length} source{turn.citations.length === 1 ? "" : "s"} retrieved
            </span>
            {badCount > 0 && (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 font-sans text-[11px] font-semibold not-italic text-red-700 ring-1 ring-red-300">
                ⚠ {badCount} unsupported citation{badCount === 1 ? "" : "s"}
              </span>
            )}
          </footer>
        )}
      </article>
      {turn.role !== "moderator" && (
        <EvidenceStrip
          evidence={turn.evidence}
          tone={eb ? "eb" : "wp"}
          attached
          pending={awaitingEvidence && turn.finished}
          citations={turn.citations}
          unsupported={turn.unsupported}
        />
      )}
    </div>
  );
}

function ordinal(n: number) {
  return ["", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"][n] ?? `${n}th`;
}

function roman(n: number) {
  return ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][n] ?? String(n);
}

/* ----------------------------- moderator ----------------------------- */

export function ModeratorCard({ turn }: { turn: Turn }) {
  const ruling = turn.finished ? parseModerator(turn.text) : null;
  const agreement = agreementOf(ruling?.points);

  if (!turn.finished) {
    return (
      <div className="animate-pop top-glow scoreboard relative z-10 mx-auto w-full max-w-3xl overflow-hidden rounded-2xl px-6 py-5 text-slate-200 shadow-[0_24px_60px_-24px_rgba(245,158,11,0.45)] ring-1 ring-white/10">
        <div className="shimmer absolute inset-0 opacity-10" />
        <div className="relative flex items-center gap-3">
          <GavelIcon />
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-300/90">
              The Moderator · Round {roman(turn.round)}
            </div>
            <div className="text-sm text-slate-300">
              <span className="dots">Weighing the arguments and checking the citations</span>
            </div>
          </div>
          <Spinner className="ml-auto text-amber-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-pop top-glow scoreboard relative z-10 mx-auto w-full max-w-3xl rounded-2xl px-5 py-5 text-slate-100 shadow-[0_24px_60px_-24px_rgba(245,158,11,0.45)] ring-1 ring-white/10 md:px-6">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <GavelIcon />
        <div>
          <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-300/90">
            The Moderator · Round {roman(turn.round)} ruling
          </div>
          <div className="text-[11px] text-slate-400">judging from the rift between the eras</div>
        </div>
        {agreement && (
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
            <span className="font-semibold text-emerald-400">{agreement.agreed} agreed</span>·
            <span className="font-semibold text-rose-400">{agreement.total - agreement.agreed} disputed</span>
          </div>
        )}
      </div>
      {ruling?.summary ? (
        <p className="text-[15px] leading-relaxed text-slate-200">{ruling.summary}</p>
      ) : (
        <CitedText text={turn.text} className="text-[15px] leading-relaxed text-slate-200" />
      )}
      {ruling?.points && ruling.points.length > 0 && (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2">
          {ruling.points.map((p, i) => (
            <li
              key={i}
              className="animate-fade-up flex flex-col gap-1.5 rounded-lg bg-white/5 px-3 py-2 ring-1 ring-white/10 transition hover:bg-white/10"
              style={{ animationDelay: `${120 + i * 80}ms` }}
            >
              <span className="text-[13px] leading-snug text-slate-100">{p.claim}</span>
              <span className="flex flex-wrap gap-1.5">
                <StatusBadge status={p.status} />
                <CategoryBadge category={p.category} />
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function GavelIcon() {
  return (
    <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-amber-300/30 to-amber-600/10 text-amber-300 shadow-[0_0_18px_-2px_rgba(251,191,36,0.55)] ring-1 ring-amber-300/40">
      <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
        <path d="m14.6 2.3 7.1 7.1-2.1 2.1-1.4-1.4-2.8 2.8 1.4 1.4-2.1 2.1-7.1-7.1 2.1-2.1 1.4 1.4 2.8-2.8-1.4-1.4 2.1-2.1ZM8.3 12.6l3.1 3.1-7.2 7.2a2.2 2.2 0 0 1-3.1-3.1l7.2-7.2ZM13 20h9v2h-9z" />
      </svg>
    </span>
  );
}

/* ----------------------------- agreement: the scales of evidence ----------------------------- */

export function AgreementMeter({
  points,
  pending,
  ebSupport = null,
  wpSupport = null,
}: {
  points: VerdictPoint[] | undefined;
  pending: boolean;
  ebSupport?: number | null;
  wpSupport?: number | null;
}) {
  const a = agreementOf(points);
  /* the better-supported side sinks; the less they agree, the further the beam tips */
  const diff = isNum(ebSupport) && isNum(wpSupport) ? wpSupport - ebSupport : 0;
  const tilt = a ? Math.sign(diff) * Math.min(1, (1 - a.pct / 100) * 0.7 + Math.min(Math.abs(diff), 0.3)) : 0;

  return (
    <div className="flex w-full flex-col items-center">
      <BalanceScale tilt={tilt} pending={pending && !a} />
      <div
        className="-mt-1 flex w-full max-w-[300px] justify-between font-mono text-[10.5px] tabular-nums"
        title="Mean Nemotron Rerank support of each side's claims by its own cited sources"
      >
        <span className="text-amber-200/85">evidence {pctOf(ebSupport)}</span>
        <span className="text-sky-200/85">{pctOf(wpSupport)} evidence</span>
      </div>
      <div className="mt-2 text-center text-xs text-slate-300">
        {a ? (
          <>
            <span className="text-3xl font-semibold tabular-nums text-white">{a.pct}%</span>
            <span className="ml-2 text-slate-400">
              agreement · {a.agreed}/{a.total} points
            </span>
          </>
        ) : (
          <span className="italic text-slate-400">
            {pending ? "The scales await the moderator's ruling…" : "Balanced — no ruling yet"}
          </span>
        )}
      </div>
    </div>
  );
}

/* ----------------------------- verdict ----------------------------- */

export function VerdictCard({ verdict, evidence }: { verdict: Verdict; evidence?: VerdictEvidence | null }) {
  const a = agreementOf(verdict.points);
  const ok = verdict.converged;
  const nAna = evidence?.anachronisms.length ?? 0;
  return (
    <section data-verdict className="animate-pop duel-frame overflow-hidden rounded-3xl bg-white">
      <div className="relative isolate overflow-hidden bg-[#0c0b12] px-6 py-8 text-white md:px-10 md:py-10">
        <div
          aria-hidden
          className={`absolute inset-0 -z-10 ${
            ok
              ? "bg-[radial-gradient(ellipse_at_85%_40%,rgba(16,185,129,0.45),transparent_55%),radial-gradient(ellipse_at_0%_100%,rgba(240,192,112,0.25),transparent_55%)]"
              : "bg-[radial-gradient(ellipse_at_85%_40%,rgba(225,29,72,0.45),transparent_55%),radial-gradient(ellipse_at_0%_100%,rgba(56,189,248,0.22),transparent_55%)]"
          }`}
        />
        <div aria-hidden className="rays pointer-events-none absolute inset-0 -z-10" />
        <div className="flex flex-col-reverse gap-6 md:flex-row md:items-center md:gap-10">
          <div className="min-w-0 flex-1">
            <div className="text-[11px] font-semibold uppercase tracking-[0.3em] text-white/60">The final verdict</div>
            <h2 className="mt-2 text-[40px] font-semibold leading-[1.02] tracking-tight md:text-6xl">
              {ok ? (
                <>
                  <span className="font-fell font-normal italic text-emerald-300">Consensus</span> reached
                </>
              ) : (
                <>
                  Still <span className="font-fell font-normal italic text-rose-300">divided</span>
                </>
              )}
            </h2>
            {verdict.summary && (
              <p className="mt-4 max-w-3xl text-[15.5px] leading-relaxed text-white/85">{verdict.summary}</p>
            )}
            {a && (
              <div className="mt-5 flex flex-wrap gap-2.5 text-sm">
                <span className="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20">
                  <strong className="tabular-nums">{a.pct}%</strong> agreement
                </span>
                <span className="rounded-full bg-white/10 px-3 py-1 ring-1 ring-white/20">
                  <span className="text-emerald-300">{a.agreed} agreed</span> ·{" "}
                  <span className="text-rose-300">{a.total - a.agreed} disputed</span>
                </span>
                {evidence && (
                  <span
                    className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 ring-1 ${
                      nAna ? "bg-red-500/30 ring-red-300/60" : "bg-white/10 ring-white/20"
                    }`}
                  >
                    <HourglassIcon className={nAna ? "hourglass-flip" : ""} /> Anachronisms detected:{" "}
                    <strong className="tabular-nums">{nAna}</strong>
                  </span>
                )}
              </div>
            )}
          </div>
          <WaxSeal ok={ok} className="h-[120px] w-[120px] shrink-0 self-center md:h-[180px] md:w-[180px]" />
        </div>
      </div>

      <div className="px-5 py-6 md:px-8">
        {evidence && <VerdictEvidencePanel evidence={evidence} />}
        <div className="mb-5 rounded-2xl bg-slate-50 p-3 ring-1 ring-slate-200 md:p-4">
          <div className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            What kind of change?
          </div>
          <CategoryLegend />
        </div>

        <div className="overflow-x-auto xl:overflow-visible">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-[11px] uppercase tracking-[0.12em] text-slate-500">
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Claim</th>
                <th className="border-b border-slate-200 px-3 py-2 font-semibold">
                  <span className="font-fell text-[14px] normal-case tracking-normal text-[#7a2e12]">Britannica</span>{" "}
                  1768–1860
                </th>
                <th className="border-b border-slate-200 px-3 py-2 font-semibold">
                  <span className="text-[12px] normal-case tracking-normal text-slate-800">Wikipedia</span> 2026
                </th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Status</th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Change</th>
                <th className="border-b border-slate-200 py-2 font-semibold">Sources</th>
              </tr>
            </thead>
            <tbody>
              {verdict.points.map((p, i) => (
                <tr key={i} className="animate-fade-up align-top" style={{ animationDelay: `${150 + i * 90}ms` }}>
                  <td className="border-b border-slate-100 py-3 pr-4 font-medium text-slate-900">{p.claim}</td>
                  <td className="border-b border-[#ecdcb6] bg-[#fbf3df] px-3 py-3 font-serif text-[15px] leading-snug text-ink">
                    {p.britannica || <span className="italic opacity-50">—</span>}
                  </td>
                  <td className="border-b border-slate-100 px-3 py-3 leading-snug text-slate-700">
                    {p.wikipedia || <span className="italic opacity-50">—</span>}
                  </td>
                  <td className="border-b border-slate-100 py-3 pr-4">
                    <StatusBadge status={p.status} />
                  </td>
                  <td className="border-b border-slate-100 py-3 pr-4">
                    <CategoryBadge category={p.category} />
                  </td>
                  <td className="border-b border-slate-100 py-3">
                    <div className="flex flex-wrap gap-1">
                      {(p.cites ?? []).map((id) => (
                        <CitationChip key={id} id={id} />
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
