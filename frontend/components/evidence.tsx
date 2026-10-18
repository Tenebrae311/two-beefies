"use client";

import { useState } from "react";
import { FLAG_META, FLAG_ORDER, isNum, pct, RERANK_LABEL, supportTone, TONE_BAR, TONE_TEXT } from "@/utils/evidence";
import type { Citation, Evidence, EvidenceClaim, VerdictEvidence } from "@/utils/types";
import { CitationChip } from "./citations";

type Tone = "eb" | "wp" | "light";

/* ----------------------------- atoms ----------------------------- */

export function HourglassIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-3.5 w-3.5 fill-current ${className}`} aria-hidden>
      <path d="M5 2h10a1 1 0 1 1 0 2h-.5v1.6a4 4 0 0 1-1.6 3.2L11.3 10l1.6 1.2a4 4 0 0 1 1.6 3.2V16h.5a1 1 0 1 1 0 2H5a1 1 0 1 1 0-2h.5v-1.6a4 4 0 0 1 1.6-3.2L8.7 10 7.1 8.8a4 4 0 0 1-1.6-3.2V4H5a1 1 0 1 1 0-2Zm2.5 2v1.6c0 .6.3 1.2.8 1.6L10 8.5l1.7-1.3c.5-.4.8-1 .8-1.6V4h-5Zm2.5 7.5-1.7 1.3c-.5.4-.8 1-.8 1.6V16h5v-1.6c0-.6-.3-1.2-.8-1.6L10 11.5Z" />
    </svg>
  );
}

export function ScaleIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-3.5 w-3.5 fill-current ${className}`} aria-hidden>
      <path d="M10 2a1 1 0 0 1 1 1v.6l4.6 1.3a1 1 0 0 1 .5.3l2.8 5.3a1 1 0 0 1 .1.5 3.5 3.5 0 0 1-7 0 1 1 0 0 1 .1-.5l2.2-4.2L11 5.7V16h3a1 1 0 1 1 0 2H6a1 1 0 1 1 0-2h3V5.7l-3.3.9 2.2 4.2a1 1 0 0 1 .1.5 3.5 3.5 0 0 1-7 0 1 1 0 0 1 .1-.5l2.8-5.3a1 1 0 0 1 .5-.3L9 3.6V3a1 1 0 0 1 1-1Zm5.5 6.1L14 11h3l-1.5-2.9Zm-11 0L3 11h3L4.5 8.1Z" />
    </svg>
  );
}

function Spinner({ className = "" }: { className?: string }) {
  return (
    <span
      className={`inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-current border-t-transparent ${className}`}
    />
  );
}

function NvidiaDot() {
  return <span className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-[#76b900]" />;
}

/** Hover / focus explanation: where the numbers come from. */
export function EvidenceInfo({ align = "left" }: { align?: "left" | "right" }) {
  return (
    <span className="group/info relative inline-flex">
      <button
        type="button"
        aria-label="How are these scores computed?"
        className="inline-flex h-4 w-4 items-center justify-center rounded-full bg-black/5 text-[10px] font-bold leading-none opacity-70 ring-1 ring-black/10 transition hover:opacity-100 focus:opacity-100"
      >
        i
      </button>
      <span
        role="tooltip"
        className={`pointer-events-none absolute bottom-full z-40 mb-2 hidden w-80 rounded-xl bg-slate-900 px-4 py-3 text-left font-sans text-[11.5px] font-normal normal-case leading-snug tracking-normal text-slate-200 shadow-2xl ring-1 ring-white/10 group-focus-within/info:block group-hover/info:block ${
          align === "left" ? "left-0" : "right-0"
        }`}
      >
        <strong className="mb-1 flex items-center gap-1.5 text-[12px] font-semibold text-white">
          <NvidiaDot /> Scored by {RERANK_LABEL}, not by the debater
        </strong>
        Each claim is paired with the passages it cites, and the Nemotron reranker scores how well those passages
        support it (0–100%). The LLM never grades itself. For the Britannica scholar every claim is also scored against
        Wikipedia: weak support from his own 18th/19th-century sources but strong support from Wikipedia means he
        smuggled in modern knowledge — an <span className="font-semibold text-amber-300">anachronism</span>.
        <span className="mt-2 grid grid-cols-1 gap-1">
          {FLAG_ORDER.map((f) => (
            <span key={f} className="flex items-center gap-2">
              <span className={`h-2 w-2 shrink-0 rounded-full ${FLAG_META[f].dot}`} />
              <span className="font-semibold text-slate-100">{FLAG_META[f].label}</span>
              <span className="text-slate-400">{FLAG_META[f].explain}</span>
            </span>
          ))}
        </span>
      </span>
    </span>
  );
}

export function SupportMeter({
  value,
  size = "sm",
  label = "supported",
  nullLabel = "reranker offline",
}: {
  value: number | null | undefined;
  size?: "sm" | "lg";
  label?: string;
  nullLabel?: string;
}) {
  if (!isNum(value)) {
    return (
      <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-200/70 px-2 py-0.5 text-[10.5px] font-semibold text-slate-600 ring-1 ring-slate-300">
        <span className="h-1.5 w-1.5 rounded-full bg-slate-400" />
        {nullLabel}
      </span>
    );
  }
  const tone = supportTone(value);
  const w = Math.max(3, Math.round(value * 100));
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`relative overflow-hidden rounded-full bg-black/10 ring-1 ring-black/5 ${
          size === "lg" ? "h-2.5 w-full min-w-24" : "h-1.5 w-16"
        }`}
      >
        <span
          className={`absolute inset-y-0 left-0 rounded-full transition-[width] duration-700 ease-out ${TONE_BAR[tone]}`}
          style={{ width: `${w}%` }}
        />
      </span>
      <span
        className={`whitespace-nowrap tabular-nums ${TONE_TEXT[tone]} ${size === "lg" ? "text-lg font-semibold" : "text-[11px] font-semibold"}`}
      >
        {pct(value)}
        {label && <span className="ml-1 text-[10.5px] font-medium opacity-70">{label}</span>}
      </span>
    </span>
  );
}

/* ----------------------------- claim rows ----------------------------- */

function ClaimRow({
  claim,
  citations,
  unsupported,
}: {
  claim: EvidenceClaim;
  citations?: Citation[];
  unsupported?: string[];
}) {
  const m = FLAG_META[claim.flag];
  const ana = claim.flag === "anachronism";
  return (
    <li className={`animate-fade-up flex items-start gap-2 rounded-lg px-2 py-1.5 ${ana ? "anachronism-row my-1.5 py-2" : m.row}`}>
      {ana ? (
        <span className="mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-red-600 to-amber-500 text-white shadow-[0_0_14px_-2px_rgba(220,38,38,0.8)]">
          <HourglassIcon className="hourglass-flip !h-3.5 !w-3.5" />
        </span>
      ) : (
        <span className={`mt-[5px] h-2 w-2 shrink-0 rounded-full ${m.dot}`} title={`${m.label}: ${m.explain}`} />
      )}
      <div className="min-w-0 flex-1">
        {ana && (
          <div className="mb-0.5 flex flex-wrap items-baseline gap-x-2 text-[10.5px] font-bold uppercase tracking-[0.1em] text-red-700">
            <span className="rounded bg-red-600 px-1.5 py-px text-white">Temporal anomaly</span>
            Anachronism — modern knowledge not in his sources
          </div>
        )}
        <span className={`text-[12.5px] leading-snug ${ana ? "glitch inline-block font-serif text-[15px] font-medium italic text-red-950" : ""}`}>
          {claim.text}
        </span>
        {claim.cites.map((id) => (
          <CitationChip key={id} id={id} citations={citations} unsupported={unsupported} />
        ))}
        {claim.flag === "uncited" && <span className="ml-1 text-[10.5px] italic opacity-60">no citation</span>}
        {ana && (
          <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] font-semibold tabular-nums">
            <span className="inline-flex items-center gap-1 text-[#7a2e12]">
              <span className="rounded-[3px] bg-[#7a2e12] px-[3px] font-fell text-[9px] leading-[14px] text-amber-50">
                EB
              </span>
              own sources {pct(claim.support)}
            </span>
            <span className="text-slate-400">·</span>
            <span className="inline-flex items-center gap-1 text-slate-800">
              <span className="rounded-[3px] bg-slate-800 px-[3px] font-serif text-[9px] leading-[14px] text-white">
                W
              </span>
              Wikipedia {pct(claim.modern_support)}
            </span>
          </div>
        )}
      </div>
      {!ana && (
        <span
          className={`mt-px shrink-0 text-[11px] font-semibold tabular-nums ${m.score}`}
          title={`${m.label}: ${m.explain}`}
        >
          {claim.flag === "uncited" ? "—" : pct(claim.support)}
        </span>
      )}
    </li>
  );
}

/* ----------------------------- the strip ----------------------------- */

const STRIP_TONE: Record<Tone, string> = {
  eb: "border-[#d8bf8c] bg-[#f1e2bf]/90 text-[#4a3018]",
  wp: "border-slate-200 bg-slate-50/95 text-slate-700",
  light: "border-slate-200 bg-white text-slate-700",
};

/**
 * Compact "Evidence (Nemotron Rerank)" strip: support meter + one row per claim, coloured by flag.
 * `attached` renders it as a tab hanging under a debate bubble.
 */
export function EvidenceStrip({
  evidence,
  tone = "light",
  pending = false,
  attached = false,
  citations,
  unsupported,
  className = "",
}: {
  evidence: Evidence | null | undefined;
  tone?: Tone;
  pending?: boolean;
  attached?: boolean;
  citations?: Citation[];
  unsupported?: string[];
  className?: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const shape = attached ? "mx-3 rounded-b-xl border border-t-0 px-3 pb-2.5 pt-2" : "rounded-xl border px-4 py-3";

  if (!evidence) {
    if (!pending) return null;
    return (
      <div className={`${shape} ${STRIP_TONE[tone]} flex items-center gap-2 text-[11px] ${className}`}>
        <Spinner className="text-[#76b900]" />
        <span className="opacity-80">{RERANK_LABEL} is checking each claim against its cited passage…</span>
      </div>
    );
  }

  const claims = evidence.claims;
  const nAna = claims.filter((c) => c.flag === "anachronism").length;
  const limit = 3;
  const collapsible = claims.length > limit + 1;
  const visible =
    !collapsible || expanded
      ? claims
      : claims.filter((c, i) => i < limit || c.flag === "anachronism" || c.flag === "unsupported");
  const hidden = claims.length - visible.length;

  return (
    <div className={`animate-fade-up ${shape} ${STRIP_TONE[tone]} ${className}`}>
      <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
        <ScaleIcon className="opacity-70" />
        <span className="text-[10.5px] font-semibold uppercase tracking-[0.14em]">Evidence</span>
        <span className="inline-flex items-center gap-1 rounded-full bg-slate-900 px-1.5 py-px text-[9.5px] font-semibold text-white">
          <NvidiaDot /> {RERANK_LABEL}
        </span>
        <EvidenceInfo />
        {nAna > 0 && (
          <span className="inline-flex items-center gap-1 rounded-full bg-red-600 px-2 py-px text-[10px] font-bold text-white shadow-sm">
            <HourglassIcon className="hourglass-flip !h-3 !w-3" />
            {nAna} anachronism{nAna === 1 ? "" : "s"}
          </span>
        )}
        <span className="ml-auto">
          <SupportMeter value={evidence.support} />
        </span>
      </div>
      {claims.length > 0 && (
        <ul className="mt-1.5 space-y-0.5">
          {visible.map((c, i) => (
            <ClaimRow key={i} claim={c} citations={citations} unsupported={unsupported} />
          ))}
        </ul>
      )}
      {collapsible && (
        <button
          type="button"
          onClick={() => setExpanded((x) => !x)}
          className="mt-1 px-2 text-[11px] font-semibold opacity-70 underline-offset-2 hover:underline hover:opacity-100"
        >
          {expanded ? "Show fewer claims" : `Show all ${claims.length} claims (+${hidden})`}
        </button>
      )}
    </div>
  );
}

/* ----------------------------- verdict section ----------------------------- */

export function VerdictEvidencePanel({ evidence }: { evidence: VerdictEvidence }) {
  const n = evidence.anachronisms.length;
  return (
    <div className="mb-4 grid gap-3 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)_minmax(0,2fr)]">
      <div className="parchment rounded-xl px-4 py-3 ring-1 ring-[#d8bf8c]">
        <div className="mb-1 font-fell text-[13px] uppercase tracking-[0.12em] text-[#7a5230]">Britannica scholar</div>
        <SupportMeter value={evidence.britannica} size="lg" label="" />
        <div className="mt-1 text-[11px] text-[#7a5230]">claims backed by his own cited pages</div>
      </div>
      <div className="modern-grid rounded-xl px-4 py-3 ring-1 ring-slate-200">
        <div className="mb-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">
          Wikipedia editor
        </div>
        <SupportMeter value={evidence.wikipedia} size="lg" label="" />
        <div className="mt-1 text-[11px] text-slate-500">claims backed by the cited articles</div>
      </div>
      <div
        className={`rounded-xl px-4 py-3 ring-1 ${
          n ? "bg-gradient-to-br from-red-50 to-amber-50 ring-red-300" : "bg-slate-50 ring-slate-200"
        }`}
      >
        <div className="flex flex-wrap items-center gap-2">
          <span
            className={`inline-flex h-6 w-6 items-center justify-center rounded-full ${
              n ? "bg-gradient-to-br from-red-600 to-amber-500 text-white shadow-[0_0_14px_-2px_rgba(220,38,38,0.8)]" : "bg-slate-200 text-slate-500"
            }`}
          >
            <HourglassIcon className={n ? "hourglass-flip" : ""} />
          </span>
          <span className={`text-sm font-semibold ${n ? "text-red-800" : "text-slate-700"}`}>
            Anachronisms detected: <span className="tabular-nums">{n}</span>
          </span>
          <span className="ml-auto inline-flex items-center gap-1.5 text-[10.5px] font-semibold text-slate-500">
            <NvidiaDot /> {RERANK_LABEL}
            <EvidenceInfo align="right" />
          </span>
        </div>
        {n === 0 ? (
          <p className="mt-1.5 text-[12.5px] text-slate-600">
            The scholar stayed within his own sources — nothing he said was known only to the modern world.
          </p>
        ) : (
          <ul className="mt-2 space-y-1.5">
            {evidence.anachronisms.map((a, i) => (
              <li key={i} className="anachronism-row rounded-lg px-3 py-2 text-[12.5px]">
                <span className="mr-2 rounded-full bg-red-100 px-1.5 py-px text-[10px] font-bold uppercase tracking-wider text-red-700">
                  Round {a.round}
                </span>
                <span className="glitch inline-block font-serif text-[15px] italic text-red-950">“{a.text}”</span>
                <div className="mt-1 text-[11px] font-semibold tabular-nums text-slate-600">
                  <span className="text-[#7a2e12]">own sources {pct(a.support)}</span>
                  <span className="mx-1.5 text-slate-400">·</span>
                  <span className="text-slate-800">Wikipedia {pct(a.modern_support)}</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
