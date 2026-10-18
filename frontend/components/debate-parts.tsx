"use client";

import { formatArgs } from "@/utils/api";
import { agreementOf, CATEGORY_META, categoryMeta, isAgreed, parseModerator } from "@/utils/cite";
import type { ToolActivity, Turn } from "@/utils/useDebate";
import type { PointCategory, Verdict, VerdictPoint } from "@/utils/types";
import { CitationChip, CitedText } from "./citations";

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
      className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-full px-2 py-0.5 text-[11px] font-semibold ring-1 ${m.badge}`}
      title={m.explain}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${m.dot}`} />
      {m.label}
    </span>
  );
}

export function CategoryLegend({ dark = false }: { dark?: boolean }) {
  return (
    <div className={`flex flex-wrap gap-x-5 gap-y-2 text-xs ${dark ? "text-slate-300" : "text-slate-600"}`}>
      {(Object.keys(CATEGORY_META) as PointCategory[]).map((k) => (
        <span key={k} className="inline-flex items-center gap-2">
          <CategoryBadge category={k} />
          <span>{CATEGORY_META[k].explain}</span>
        </span>
      ))}
    </div>
  );
}

/* ----------------------------- tool activity ----------------------------- */

export function ToolPill({ tool, tone }: { tool: ToolActivity; tone: "eb" | "wp" }) {
  const base =
    tone === "eb"
      ? "bg-[#ecd9b0]/70 text-[#5b3410] ring-[#c9a46a]/60"
      : "bg-sky-50 text-sky-800 ring-sky-200";
  return (
    <div
      className={`animate-fade-up inline-flex max-w-full items-center gap-1.5 rounded-md px-2 py-1 font-mono text-[11px] ring-1 ${base}`}
    >
      {tool.done ? <SearchIcon /> : <Spinner />}
      <span className="truncate">
        {tool.name}({formatArgs(tool.args)})
      </span>
      {tool.done && (
        <span className="ml-1 shrink-0 rounded bg-black/5 px-1 font-sans font-semibold">
          {tool.hits?.length ?? 0} hit{tool.hits?.length === 1 ? "" : "s"}
        </span>
      )}
    </div>
  );
}

/* ----------------------------- turn bubbles ----------------------------- */

export function TurnBubble({ turn }: { turn: Turn }) {
  const eb = turn.role === "britannica";
  const streaming = !turn.finished;
  const searching = turn.tools.some((t) => !t.done);
  const badCount = turn.unsupported.length;

  return (
    <article
      className={`animate-fade-up relative rounded-2xl p-5 shadow-sm transition-shadow ${
        eb
          ? "border border-[#d8bf8c] bg-[#fbf3df]/90 text-ink shadow-[0_6px_20px_-12px_rgba(90,55,20,0.45)]"
          : "border border-slate-200 bg-white text-slate-800 shadow-[0_6px_20px_-14px_rgba(15,23,42,0.35)]"
      } ${streaming ? (eb ? "ring-2 ring-[#c9a46a]/50" : "ring-2 ring-sky-300/50") : ""}`}
    >
      <header className="mb-3 flex items-center justify-between gap-2">
        <span
          className={
            eb
              ? "font-fell text-[15px] italic text-[#7a2e12]"
              : "text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500"
          }
        >
          {eb ? `The ${ordinal(turn.round)} Round` : `Round ${turn.round} · Editor`}
        </span>
        {streaming && (
          <span className={`inline-flex items-center gap-1.5 text-[11px] ${eb ? "text-[#7a5230]" : "text-sky-700"}`}>
            <Spinner />
            {searching ? "searching…" : "writing…"}
          </span>
        )}
      </header>

      {turn.tools.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-1.5">
          {turn.tools.map((t, i) => (
            <ToolPill key={i} tool={t} tone={eb ? "eb" : "wp"} />
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
            eb ? "border-[#e2cd9f] text-[#7a5230]" : "border-slate-100 text-slate-500"
          }`}
        >
          <span>
            {turn.citations.length} source{turn.citations.length === 1 ? "" : "s"} retrieved
          </span>
          {badCount > 0 && (
            <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 font-semibold text-red-700 ring-1 ring-red-300">
              ⚠ {badCount} unsupported citation{badCount === 1 ? "" : "s"}
            </span>
          )}
        </footer>
      )}
    </article>
  );
}

function ordinal(n: number) {
  return ["", "First", "Second", "Third", "Fourth", "Fifth", "Sixth", "Seventh", "Eighth"][n] ?? `${n}th`;
}

/* ----------------------------- moderator ----------------------------- */

export function ModeratorCard({ turn }: { turn: Turn }) {
  const ruling = turn.finished ? parseModerator(turn.text) : null;
  const agreement = agreementOf(ruling?.points);

  if (!turn.finished) {
    return (
      <div className="animate-fade-up relative mx-auto w-full max-w-3xl overflow-hidden rounded-2xl bg-slate-900 px-6 py-5 text-slate-200 shadow-xl ring-1 ring-white/10">
        <div className="shimmer absolute inset-0 opacity-10" />
        <div className="relative flex items-center gap-3">
          <GavelIcon />
          <div>
            <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-300/90">
              Moderator · Round {turn.round}
            </div>
            <div className="text-sm text-slate-300">Weighing the arguments and checking the citations…</div>
          </div>
          <Spinner className="ml-auto text-amber-300" />
        </div>
      </div>
    );
  }

  return (
    <div className="animate-fade-up mx-auto w-full max-w-3xl rounded-2xl bg-slate-900 px-6 py-5 text-slate-100 shadow-xl ring-1 ring-white/10">
      <div className="mb-3 flex flex-wrap items-center gap-3">
        <GavelIcon />
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-amber-300/90">
          Moderator · Round {turn.round} ruling
        </div>
        {agreement && (
          <div className="ml-auto flex items-center gap-2 text-xs text-slate-400">
            <span className="text-emerald-400">{agreement.agreed} agreed</span>·
            <span className="text-rose-400">{agreement.total - agreement.agreed} disputed</span>
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
              className="flex flex-col gap-1.5 rounded-lg bg-white/5 px-3 py-2 ring-1 ring-white/10"
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
    <span className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-amber-400/15 text-amber-300 ring-1 ring-amber-300/30">
      <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current">
        <path d="m14.6 2.3 7.1 7.1-2.1 2.1-1.4-1.4-2.8 2.8 1.4 1.4-2.1 2.1-7.1-7.1 2.1-2.1 1.4 1.4 2.8-2.8-1.4-1.4 2.1-2.1ZM8.3 12.6l3.1 3.1-7.2 7.2a2.2 2.2 0 0 1-3.1-3.1l7.2-7.2ZM13 20h9v2h-9z" />
      </svg>
    </span>
  );
}

/* ----------------------------- agreement meter ----------------------------- */

export function AgreementMeter({
  points,
  pending,
}: {
  points: VerdictPoint[] | undefined;
  pending: boolean;
}) {
  const a = agreementOf(points);
  const pct = a?.pct ?? 50;
  return (
    <div className="w-full">
      <div className="mb-1.5 flex items-end justify-between text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
        <span>Disagree</span>
        <span className="text-[11px] tracking-[0.2em] text-slate-300">Agreement</span>
        <span>Agree</span>
      </div>
      <div className="relative h-3.5 w-full overflow-hidden rounded-full bg-slate-700/70 ring-1 ring-white/10">
        {a ? (
          <div
            className="h-full rounded-full bg-gradient-to-r from-rose-500 via-amber-400 to-emerald-400 transition-[width] duration-1000 ease-out"
            style={{ width: `${Math.max(pct, 4)}%` }}
          />
        ) : (
          <div
            className={`h-full w-full ${pending ? "shimmer" : ""}`}
            style={{
              backgroundImage:
                "repeating-linear-gradient(45deg, rgba(255,255,255,0.08) 0 6px, transparent 6px 12px)",
            }}
          />
        )}
        <div className="absolute inset-y-0 left-1/2 w-px bg-white/30" />
      </div>
      <div className="mt-1.5 text-center text-xs text-slate-300">
        {a ? (
          <>
            <span className="text-lg font-semibold tabular-nums text-white">{pct}%</span>
            <span className="ml-2 text-slate-400">
              {a.agreed}/{a.total} points agreed
            </span>
          </>
        ) : (
          <span className="italic text-slate-400">{pending ? "Awaiting the moderator's ruling…" : "Neutral — no ruling yet"}</span>
        )}
      </div>
    </div>
  );
}

/* ----------------------------- verdict ----------------------------- */

export function VerdictCard({ verdict }: { verdict: Verdict }) {
  const a = agreementOf(verdict.points);
  const ok = verdict.converged;
  return (
    <section className="animate-pop overflow-hidden rounded-3xl bg-white shadow-2xl ring-1 ring-slate-200">
      <div
        className={`relative px-8 py-7 text-white ${
          ok
            ? "bg-gradient-to-br from-emerald-700 via-emerald-800 to-slate-900"
            : "bg-gradient-to-br from-rose-700 via-rose-800 to-slate-900"
        }`}
      >
        <div className="text-[11px] font-semibold uppercase tracking-[0.22em] text-white/70">Final verdict</div>
        <h2 className="mt-1 flex items-center gap-3 text-4xl font-semibold tracking-tight">
          <span className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-white/15 text-2xl ring-1 ring-white/30">
            {ok ? "✓" : "⚖"}
          </span>
          {ok ? "Consensus reached" : "Still disagreeing"}
        </h2>
        {verdict.summary && <p className="mt-4 max-w-4xl text-[15.5px] leading-relaxed text-white/90">{verdict.summary}</p>}
        {a && (
          <div className="mt-5 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full bg-white/15 px-3 py-1 ring-1 ring-white/20">
              <strong className="tabular-nums">{a.pct}%</strong> agreement
            </span>
            <span className="rounded-full bg-white/15 px-3 py-1 ring-1 ring-white/20">
              {a.agreed} agreed · {a.total - a.agreed} disputed
            </span>
          </div>
        )}
      </div>

      <div className="px-8 py-6">
        <div className="mb-4 rounded-xl bg-slate-50 px-4 py-3 ring-1 ring-slate-200">
          <div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500">
            What kind of change?
          </div>
          <CategoryLegend />
        </div>

        <div className="overflow-x-auto xl:overflow-visible">
          <table className="w-full min-w-[760px] border-separate border-spacing-0 text-left text-sm">
            <thead>
              <tr className="text-[11px] uppercase tracking-[0.12em] text-slate-500">
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Claim</th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">
                  <span className="font-fell text-[13px] normal-case tracking-normal text-[#7a2e12]">Britannica</span>{" "}
                  1768–1860
                </th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">
                  <span className="text-[12px] normal-case tracking-normal text-slate-800">Wikipedia</span> 2026
                </th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Status</th>
                <th className="border-b border-slate-200 py-2 pr-4 font-semibold">Change</th>
                <th className="border-b border-slate-200 py-2 font-semibold">Sources</th>
              </tr>
            </thead>
            <tbody>
              {verdict.points.map((p, i) => (
                <tr
                  key={i}
                  className="animate-fade-up align-top"
                  style={{ animationDelay: `${150 + i * 90}ms` }}
                >
                  <td className="border-b border-slate-100 py-3 pr-4 font-medium text-slate-900">{p.claim}</td>
                  <td className="border-b border-slate-100 bg-[#fbf3df]/60 px-3 py-3 font-serif text-[15px] leading-snug text-ink">
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
