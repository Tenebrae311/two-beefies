"use client";

/* Signature pieces of the "duel across 250 years" look: era timeline with a rolling year counter,
   the fight-card intro, the balance scale, the wax seal and the small category / pipeline icons. */

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import type { PointCategory } from "@/utils/types";
import { VsMedallion } from "./flair";

export function prefersReducedMotion(): boolean {
  return typeof window !== "undefined" && window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
}

/* ------------------------------ colour helpers ------------------------------ */

const ERA_STOPS: [number, [number, number, number]][] = [
  [0, [240, 192, 112]], // gold
  [0.55, [244, 140, 80]], // ember
  [0.8, [167, 139, 250]], // violet
  [1, [56, 189, 248]], // cyan
];

/** 0 → Britannica gold, 1 → Wikipedia cyan. */
export function eraColor(t: number): string {
  const x = Math.max(0, Math.min(1, t));
  for (let i = 1; i < ERA_STOPS.length; i++) {
    const [p1, c1] = ERA_STOPS[i];
    const [p0, c0] = ERA_STOPS[i - 1];
    if (x <= p1) {
      const k = (x - p0) / (p1 - p0 || 1);
      const c = c0.map((v, j) => Math.round(v + (c1[j] - v) * k));
      return `rgb(${c[0]}, ${c[1]}, ${c[2]})`;
    }
  }
  return "rgb(56, 189, 248)";
}

/* ------------------------------ era timeline + year counter ------------------------------ */

/* the eight Britannica editions in the corpus (first year of publication) */
const EDITIONS: [number, string][] = [
  [1768, "1st"],
  [1777, "2nd"],
  [1788, "3rd"],
  [1801, "4th"],
  [1810, "5th"],
  [1820, "6th"],
  [1830, "7th"],
  [1853, "8th"],
];

/* track proportions: Britannica 1768–1860 | the gap 1860–2026 | Wikipedia */
const EB_W = 5;
const GAP_W = 3;
const WP_W = 1;
const TOTAL_W = EB_W + GAP_W + WP_W;

/** year → horizontal position (0..1) on the compressed track */
function yearToX(y: number): number {
  if (y <= 1860) return (((y - 1768) / 92) * EB_W) / TOTAL_W;
  if (y < 2026) return (EB_W + ((y - 1860) / 166) * GAP_W) / TOTAL_W;
  return 1;
}

const ease = (t: number) => (t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2);

/** progress 0..1 → year: a slow walk through the editions, then a rush across the 166-year gap. */
function sweepYear(p: number): number {
  if (p <= 0.6) return 1768 + ease(p / 0.6) * 92;
  return 1860 + ease((p - 0.6) / 0.4) * 166;
}

function useYearSweep(duration = 3400, delay = 500) {
  const [p, setP] = useState(0);
  const raf = useRef(0);
  const run = useCallback(
    (wait: number) => {
      cancelAnimationFrame(raf.current);
      let t0 = 0;
      const tick = (now: number) => {
        if (!t0) t0 = now + wait;
        if (prefersReducedMotion()) {
          setP(1);
          return;
        }
        const k = Math.max(0, Math.min(1, (now - t0) / duration));
        setP(k);
        if (k < 1) raf.current = requestAnimationFrame(tick);
      };
      raf.current = requestAnimationFrame(tick);
    },
    [duration],
  );
  useEffect(() => {
    run(delay);
    return () => cancelAnimationFrame(raf.current);
  }, [run, delay]);
  return { year: Math.round(sweepYear(p)), progress: p, replay: () => run(0) };
}

export function EraTimeline() {
  const { year, replay } = useYearSweep();
  const x = yearToX(year);
  const color = eraColor(x);
  const edition = [...EDITIONS].reverse().find(([y]) => year >= y);
  const phase =
    year >= 2026
      ? "Wikipedia · live"
      : year > 1860
        ? `${year - 1860} years after the 8th edition`
        : edition
          ? `Britannica, ${edition[1]} edition`
          : "";

  return (
    <div
      className="mx-auto w-full max-w-4xl select-none"
      aria-label="Eight Britannica editions, 1768–1860, then Wikipedia in 2026"
    >
      <div className="relative flex h-10 items-center">
        {/* Britannica stretch */}
        <div className="relative h-full" style={{ flex: EB_W }}>
          <div className="absolute inset-x-0 top-1/2 h-[2px] -translate-y-1/2 rounded-full bg-gradient-to-r from-[#b4532a] to-[#f0c070]" />
          {EDITIONS.map(([y, ed]) => {
            const lit = year >= y;
            return (
              <div
                key={y}
                className="group absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
                style={{ left: `${((y - 1768) / 92) * 100}%` }}
                title={`${ed} edition · ${y}`}
              >
                <span
                  className={`block h-2.5 w-2.5 rounded-full ring-2 ring-[#1a0e08] transition duration-300 group-hover:scale-150 ${
                    lit ? "bg-[#f5d08a] shadow-[0_0_10px_2px_rgba(240,192,112,0.75)]" : "bg-[#6b4a26]"
                  }`}
                />
                <span
                  className={`absolute bottom-4 left-1/2 hidden -translate-x-1/2 whitespace-nowrap font-mono text-[10px] transition-colors sm:block ${
                    lit ? "text-amber-200/80" : "text-amber-200/30"
                  }`}
                >
                  {ed}
                </span>
              </div>
            );
          })}
        </div>
        {/* the gap */}
        <div className="relative flex h-full items-center" style={{ flex: GAP_W }}>
          <div className="h-px w-full border-t border-dashed border-white/25" />
          <span className="absolute bottom-[26px] left-1/2 hidden -translate-x-1/2 whitespace-nowrap font-mono text-[10px] uppercase tracking-[0.18em] text-white/45 sm:block">
            166 years later
          </span>
        </div>
        {/* Wikipedia */}
        <div className="relative flex h-full items-center" style={{ flex: WP_W }}>
          <div className="h-[2px] w-full rounded-full bg-gradient-to-r from-[#818cf8] to-[#38bdf8]" />
          <span
            className={`absolute right-0 top-1/2 h-3.5 w-3.5 -translate-y-1/2 translate-x-1/2 rounded-full ring-2 ring-[#071a33] transition duration-500 ${
              year >= 2026 ? "bg-sky-300 shadow-[0_0_16px_5px_rgba(56,189,248,0.75)]" : "bg-sky-900"
            }`}
          />
        </div>
        {/* playhead: where in history we are */}
        <span
          aria-hidden
          className="pointer-events-none absolute top-1/2 -translate-x-1/2 -translate-y-1/2"
          style={{ left: `${x * 100}%` }}
        >
          <span
            className="block h-5 w-5 rounded-full border-2 border-white/90"
            style={{ boxShadow: `0 0 18px 6px ${color}`, background: color }}
          />
        </span>
      </div>

      <div className="mt-1 grid grid-cols-[1fr_auto_1fr] items-center gap-3 font-mono text-[11px] tracking-wider">
        <span className="text-amber-200/80">1768</span>
        <button
          type="button"
          onClick={replay}
          title="Replay the journey"
          className="group flex flex-col items-center rounded-2xl bg-black/35 px-5 py-1.5 ring-1 ring-white/10 backdrop-blur transition hover:bg-black/50"
        >
          <span className="flex items-baseline gap-2">
            <span className="font-fell text-[13px] italic tracking-normal text-white/55">
              {year <= 1860 ? "anno" : "year"}
            </span>
            <span
              className="text-[28px] font-semibold leading-none tabular-nums tracking-tight md:text-[34px]"
              style={{ color, textShadow: `0 0 24px ${color}` }}
              aria-live="off"
            >
              {year}
            </span>
          </span>
          <span className="mt-0.5 text-[10px] uppercase tracking-[0.16em] text-white/45">{phase}</span>
        </button>
        <span className="text-right text-sky-300/90">2026</span>
      </div>
    </div>
  );
}

/* ------------------------------ fight-card intro ------------------------------ */

/** ≈2 s "tale of the tape" shown when a debate starts. Purely decorative: the debate runs underneath; click / Esc skips. */
export function FightCard({ topic, onDone }: { topic: string; onDone: () => void }) {
  useEffect(() => {
    const id = setTimeout(onDone, 2100);
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onDone();
    window.addEventListener("keydown", onKey);
    return () => {
      clearTimeout(id);
      window.removeEventListener("keydown", onKey);
    };
  }, [onDone]);

  // Portal: the tab panels animate with a transform, which would trap position:fixed.
  return createPortal(
    <div
      role="dialog"
      aria-label={`Debate starting: ${topic}`}
      onClick={onDone}
      className="fc-overlay fixed inset-0 z-[70] cursor-pointer overflow-hidden bg-[#07060b]/85 backdrop-blur-sm"
    >
      <div className="absolute inset-0 grid grid-rows-2 md:grid-cols-2 md:grid-rows-1">
        <div className="fc-left fc-eb flex items-end justify-center px-6 pb-16 md:items-center md:justify-end md:pb-0 md:pr-[12%]">
          <div className="text-center md:text-right">
            <div className="font-fell text-xs uppercase tracking-[0.35em] text-amber-200/70 md:text-sm">
              In the left corner
            </div>
            <div className="text-eb-gradient mt-2 font-fell text-[clamp(2.2rem,5.5vw,5rem)] italic leading-[1.02]">
              The Britannica
              <br />
              Scholar
            </div>
            <div className="mt-3 font-fell text-lg text-amber-100/80 md:text-xl">
              ❦ est. 1768 · Edinburgh · eight editions ❦
            </div>
          </div>
        </div>
        <div className="fc-right fc-wp flex items-start justify-center px-6 pt-16 md:items-center md:justify-start md:pl-[12%] md:pt-0">
          <div className="text-center md:text-left">
            <div className="text-xs font-semibold uppercase tracking-[0.35em] text-sky-200/70 md:text-sm">
              In the right corner
            </div>
            <div className="text-wp-gradient mt-2 text-[clamp(2.2rem,5.5vw,5rem)] font-semibold leading-[1.02] tracking-tight">
              The Wikipedia
              <br />
              Editor
            </div>
            <div className="mt-3 font-mono text-sm text-sky-100/80 md:text-base">rev. 2026 · live · CC BY-SA</div>
          </div>
        </div>
      </div>
      <div className="rift pointer-events-none absolute left-0 right-0 top-1/2 h-[3px] -translate-y-1/2 md:bottom-0 md:left-1/2 md:right-auto md:top-0 md:h-auto md:w-[3px] md:-translate-x-1/2 md:translate-y-0" />
      <div className="fc-vs absolute left-1/2 top-1/2 -ml-[52px] -mt-[52px]">
        <VsMedallion size={104} />
      </div>
      <div className="fc-topic absolute inset-x-0 bottom-[8%] flex justify-center px-4">
        <span className="flex max-w-full flex-col items-center rounded-2xl bg-[#0c0b12]/90 px-8 py-3 text-center shadow-2xl ring-1 ring-white/15">
          <span className="text-[10.5px] font-semibold uppercase tracking-[0.4em] text-white/60">Tonight&apos;s subject</span>
          <span className="max-w-full truncate font-fell text-3xl leading-tight text-white md:text-5xl">{topic}</span>
        </span>
      </div>
      <span className="absolute bottom-4 right-5 text-[11px] text-white/45">click or Esc to skip</span>
    </div>,
    document.body,
  );
}

/* ------------------------------ balance scale ------------------------------ */

/**
 * The scales of evidence. `tilt` in −1..1: positive sinks the Wikipedia pan, negative the Britannica pan.
 * `pending` (no ruling yet) makes the beam sway.
 */
export function BalanceScale({ tilt, pending }: { tilt: number; pending: boolean }) {
  const deg = Math.max(-1, Math.min(1, tilt)) * 14;
  const rad = (deg * Math.PI) / 180;
  const L = 108;
  const px = 150;
  const py = 30;
  const right = { x: px + L * Math.cos(rad), y: py + L * Math.sin(rad) };
  const left = { x: px - L * Math.cos(rad), y: py - L * Math.sin(rad) };
  const pivot = { transformBox: "view-box", transformOrigin: `${px}px ${py}px` } as const;

  return (
    <svg viewBox="0 0 300 136" className="w-full max-w-[300px] overflow-visible" aria-hidden>
      <defs>
        <linearGradient id="beam-g" x1="0" x2="1">
          <stop offset="0" stopColor="#f0c070" />
          <stop offset="0.5" stopColor="#e2e8f0" />
          <stop offset="1" stopColor="#38bdf8" />
        </linearGradient>
        <linearGradient id="post-g" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0" stopColor="#e2e8f0" />
          <stop offset="1" stopColor="#64748b" />
        </linearGradient>
        <radialGradient id="pan-eb" cx="0.4" cy="0.2">
          <stop offset="0" stopColor="#fde7b0" />
          <stop offset="1" stopColor="#b4532a" />
        </radialGradient>
        <radialGradient id="pan-wp" cx="0.4" cy="0.2">
          <stop offset="0" stopColor="#e0f2fe" />
          <stop offset="1" stopColor="#4f46e5" />
        </radialGradient>
      </defs>
      {/* post + base */}
      <rect x="147" y={py} width="6" height="88" rx="2" fill="url(#post-g)" />
      <path d="M118 128 L182 128 L172 118 L128 118 Z" fill="#94a3b8" />
      <rect x="110" y="128" width="80" height="5" rx="2" fill="#64748b" />
      <g className={pending ? "scale-sway" : undefined} style={pivot}>
        {/* beam */}
        <g className="scale-move" style={{ ...pivot, transform: `rotate(${deg}deg)` }}>
          <rect x={px - L - 4} y={py - 2.5} width={2 * L + 8} height="5" rx="2.5" fill="url(#beam-g)" />
          <circle cx={px - L} cy={py} r="3.5" fill="#f0c070" />
          <circle cx={px + L} cy={py} r="3.5" fill="#38bdf8" />
        </g>
        {/* pans hang straight down from the beam ends */}
        <g className="scale-move" style={{ transform: `translate(${left.x}px, ${left.y}px)` }}>
          <path d="M0 0 L-28 44 M0 0 L28 44" stroke="#f0c070" strokeOpacity="0.7" strokeWidth="1.2" />
          <path d="M-34 44 Q0 66 34 44 Z" fill="url(#pan-eb)" stroke="#f5d08a" strokeWidth="1" />
          <text x="0" y="52.5" textAnchor="middle" className="font-fell" fontSize="10" fill="#3b1a08">
            EB
          </text>
        </g>
        <g className="scale-move" style={{ transform: `translate(${right.x}px, ${right.y}px)` }}>
          <path d="M0 0 L-28 44 M0 0 L28 44" stroke="#7dd3fc" strokeOpacity="0.7" strokeWidth="1.2" />
          <path d="M-34 44 Q0 66 34 44 Z" fill="url(#pan-wp)" stroke="#bae6fd" strokeWidth="1" />
          <text x="0" y="52.5" textAnchor="middle" fontSize="10" fontWeight="700" fill="#f8fafc" fontFamily="serif">
            W
          </text>
        </g>
      </g>
      {/* pivot jewel */}
      <circle cx={px} cy={py} r="7" fill="#0c0b12" stroke="url(#beam-g)" strokeWidth="2" />
      <circle cx={px} cy={py} r="2.5" fill="#fff" />
    </svg>
  );
}

/* ------------------------------ wax seal ------------------------------ */

function sealPath(cx: number, cy: number, r: number, bumps = 26): string {
  const pts: string[] = [];
  const n = bumps * 6;
  for (let i = 0; i <= n; i++) {
    const a = (i / n) * Math.PI * 2;
    const rr = r + 3.2 * Math.sin(a * bumps) + 1.6 * Math.sin(a * 7 + 1.3) + 1.1 * Math.cos(a * 3);
    pts.push(`${(cx + rr * Math.cos(a)).toFixed(2)} ${(cy + rr * Math.sin(a)).toFixed(2)}`);
  }
  return `M${pts.join(" L")} Z`;
}
const SEAL_PATH = sealPath(100, 100, 88);

/** A wax seal that stamps in: "CONSENSUS" (emerald) or "STILL DIVIDED" (crimson). */
export function WaxSeal({ ok, size, className = "" }: { ok: boolean; size?: number; className?: string }) {
  const id = ok ? "seal-ok" : "seal-no";
  const wax = ok ? ["#6ee7b7", "#047857", "#022c22"] : ["#fda4af", "#be123c", "#4c0519"];
  const word = ok ? "CONSENSUS" : "STILL DIVIDED";
  return (
    <span className={`relative inline-block ${className}`} style={size ? { width: size, height: size } : undefined}>
      <span
        aria-hidden
        className="seal-ripple absolute inset-0 rounded-full"
        style={{ boxShadow: `0 0 0 3px ${wax[0]}` }}
      />
      <svg viewBox="0 0 200 200" className="seal-stamp relative h-full w-full drop-shadow-[0_14px_22px_rgba(0,0,0,0.55)]" role="img" aria-label={word}>
        <defs>
          <radialGradient id={`${id}-wax`} cx="0.36" cy="0.3" r="0.8">
            <stop offset="0" stopColor={wax[0]} />
            <stop offset="0.45" stopColor={wax[1]} />
            <stop offset="1" stopColor={wax[2]} />
          </radialGradient>
          <path id={`${id}-ring`} d="M100 100 m-62 0 a62 62 0 1 1 124 0 a62 62 0 1 1 -124 0" />
        </defs>
        <path d={SEAL_PATH} fill={`url(#${id}-wax)`} />
        <circle cx="100" cy="100" r="74" fill="none" stroke={wax[2]} strokeOpacity="0.55" strokeWidth="3" />
        <circle cx="100" cy="100" r="73" fill="none" stroke="#fff" strokeOpacity="0.18" strokeWidth="1" />
        <circle cx="100" cy="100" r="47" fill="none" stroke={wax[2]} strokeOpacity="0.5" strokeWidth="2" />
        <text fontSize="15" fontWeight="800" letterSpacing="2" fill={wax[2]} fillOpacity="0.55" dy="1.2">
          <textPath href={`#${id}-ring`} startOffset="0" textLength="384" lengthAdjust="spacing">
            {`✦ ${word} ✦ 1768 · 2026 `}
          </textPath>
        </text>
        <text fontSize="15" fontWeight="800" letterSpacing="2" fill="#fff" fillOpacity="0.88">
          <textPath href={`#${id}-ring`} startOffset="0" textLength="384" lengthAdjust="spacing">
            {`✦ ${word} ✦ 1768 · 2026 `}
          </textPath>
        </text>
        {ok ? (
          <path
            d="M78 101 L94 117 L124 84"
            fill="none"
            stroke="#fff"
            strokeOpacity="0.92"
            strokeWidth="9"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        ) : (
          <g fill="none" stroke="#fff" strokeOpacity="0.92" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M100 76 V122 M84 124 H116 M76 86 H124" />
            <path d="M76 86 L66 106 Q76 114 86 106 Z M124 86 L114 106 Q124 114 134 106 Z" strokeWidth="3.5" />
          </g>
        )}
      </svg>
    </span>
  );
}

/* ------------------------------ icons ------------------------------ */

function Stroke({ children, className = "" }: { children: ReactNode; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      className={`h-3.5 w-3.5 shrink-0 fill-none stroke-current ${className}`}
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      {children}
    </svg>
  );
}

/** language = quill · knowledge = lightbulb · perspective = eye/lens · no counterpart = empty frame */
export function CategoryIcon({ category, className = "" }: { category: PointCategory; className?: string }) {
  switch (category) {
    case "language":
      return (
        <Stroke className={className}>
          <path d="M20 3.5C12.5 4 7.5 9 5.8 16.5L4 21" />
          <path d="M20 3.5c-.4 6.2-4.6 10.6-11.4 12.4" />
          <path d="M10 12.5l4.5-1.6" />
        </Stroke>
      );
    case "knowledge":
      return (
        <Stroke className={className}>
          <path d="M9 18h6M10 21.5h4" />
          <path d="M12 2.5a6.2 6.2 0 0 0-3.7 11.2c.7.6 1.1 1.4 1.1 2.3h5.2c0-.9.4-1.7 1.1-2.3A6.2 6.2 0 0 0 12 2.5Z" />
        </Stroke>
      );
    case "perspective":
      return (
        <Stroke className={className}>
          <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z" />
          <circle cx="12" cy="12" r="3" />
        </Stroke>
      );
    default:
      return (
        <Stroke className={className}>
          <rect x="4" y="4" width="16" height="16" rx="1.5" strokeDasharray="3.2 2.6" />
        </Stroke>
      );
  }
}

export function StageIcon({ stage, className = "" }: { stage: string; className?: string }) {
  switch (stage) {
    case "parse":
      return (
        <Stroke className={className}>
          <path d="M6 2.5h8l4 4v15H6z" />
          <path d="M14 2.5v4h4M9 11h6M9 14.5h6M9 18h4" />
        </Stroke>
      );
    case "retrieval":
      return (
        <Stroke className={className}>
          <circle cx="10.5" cy="10.5" r="6.5" />
          <path d="m15.5 15.5 5 5" />
        </Stroke>
      );
    case "rerank":
      return (
        <Stroke className={className}>
          <path d="M4 6h16M4 12h11M4 18h6" />
        </Stroke>
      );
    case "agent":
      return (
        <Stroke className={className}>
          <path d="M12 3c.6 4.2 2.8 6.4 7 7-4.2.6-6.4 2.8-7 7-.6-4.2-2.8-6.4-7-7 4.2-.6 6.4-2.8 7-7Z" />
          <path d="M19 16.5c.2 1.4.9 2.1 2.3 2.3-1.4.2-2.1.9-2.3 2.3-.2-1.4-.9-2.1-2.3-2.3 1.4-.2 2.1-.9 2.3-2.3Z" />
        </Stroke>
      );
    case "grounding":
      return (
        <Stroke className={className}>
          <circle cx="12" cy="5" r="2.2" />
          <path d="M12 7.2V21M5 13a7 7 0 0 0 14 0M8.5 10.5h7" />
        </Stroke>
      );
    default:
      return (
        <Stroke className={className}>
          <circle cx="12" cy="12" r="8" />
        </Stroke>
      );
  }
}
