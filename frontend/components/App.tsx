"use client";

import { useEffect, useState, useSyncExternalStore, type ReactNode } from "react";
import { BACKEND_URL, isMockRequested } from "@/utils/api";
import { AskView } from "./AskView";
import { CasesView } from "./CasesView";
import { CitationProvider } from "./citations";
import { DebateView } from "./DebateView";
import {
  DossierIcon,
  KnowledgeNet,
  Orrery,
  QuestionIcon,
  SwordsIcon,
  VsMedallion,
} from "./flair";
import { EraTimeline } from "./duel";

type Tab = "debate" | "ask" | "cases";
const TABS: readonly Tab[] = ["debate", "ask", "cases"];

const NAV: readonly [Tab, string, string, ReactNode][] = [
  ["debate", "Debate", "Two agents argue across time", <SwordsIcon key="d" />],
  ["ask", "Ask", "One agent, both encyclopaedias", <QuestionIcon key="a" />],
  ["cases", "Cases", "3 wins, 3 failures, dissected", <DossierIcon key="c" />],
];

const noopSubscribe = () => () => {};

export function App() {
  const mock = useSyncExternalStore(noopSubscribe, isMockRequested, () => false);
  const [tab, setTab] = useState<Tab>("debate");

  /* ?tab=cases|ask opens a tab directly (handy for demos: /?mock=1&tab=cases) */
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("tab") as Tab | null;
    if (!t || !TABS.includes(t)) return;
    const id = setTimeout(() => setTab(t), 0);
    return () => clearTimeout(id);
  }, []);

  return (
    <CitationProvider offline={mock}>
      <header className="hero relative isolate overflow-hidden text-white">
        {/* the two eras, split along a glowing diagonal seam */}
        <div aria-hidden className="hero-eb absolute inset-0 -z-10" />
        <div aria-hidden className="hero-wp absolute inset-0 -z-10" />
        <Orrery className="pointer-events-none absolute -left-40 top-1/2 -z-10 h-[620px] w-[620px] -translate-y-1/2 opacity-70 md:-left-24" />
        <KnowledgeNet className="pointer-events-none absolute -right-24 top-6 -z-10 h-[460px] w-[520px] opacity-60 md:right-0" />
        <svg
          aria-hidden
          className="pointer-events-none absolute inset-0 -z-10 h-full w-full"
          viewBox="0 0 100 100"
          preserveAspectRatio="none"
        >
          <defs>
            <linearGradient id="seam-grad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0" stopColor="#f0c070" />
              <stop offset="1" stopColor="#38bdf8" />
            </linearGradient>
          </defs>
          <line
            x1="57"
            y1="0"
            x2="43"
            y2="100"
            stroke="url(#seam-grad)"
            strokeWidth="1.5"
            vectorEffect="non-scaling-stroke"
            className="seam"
          />
        </svg>
        <div aria-hidden className="absolute inset-x-0 bottom-0 -z-10 h-24 bg-gradient-to-t from-black/50 to-transparent" />

        <div className="mx-auto flex max-w-[1500px] flex-col gap-7 px-5 pb-7 pt-6 md:px-10">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2 rounded-full bg-black/30 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-white/80 ring-1 ring-white/10 backdrop-blur">
              <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#76b900] shadow-[0_0_8px_2px_rgba(118,185,0,0.7)]" />
              NVIDIA Nemotron Challenge
            </div>
            <div className="flex items-center gap-2 rounded-full bg-black/30 px-3 py-1.5 text-xs text-slate-200 ring-1 ring-white/10 backdrop-blur">
              <span
                className={`h-2 w-2 rounded-full ${
                  mock
                    ? "bg-amber-400 shadow-[0_0_8px_2px_rgba(251,191,36,0.6)]"
                    : "bg-emerald-400 shadow-[0_0_8px_2px_rgba(52,211,153,0.6)]"
                }`}
              />
              {mock ? "Mock mode (recorded demo)" : `Live · ${BACKEND_URL.replace(/^https?:\/\//, "")}`}
            </div>
          </div>

          <div className="flex flex-col items-center text-center">
            <div className="mb-3 text-[11px] font-semibold uppercase tracking-[0.42em] text-white/60 md:text-xs">
              Knowledge Across Time
            </div>
            <h1 className="grid w-full items-center gap-2 md:grid-cols-[1fr_auto_1fr] md:gap-8">
              <span className="md:text-right">
                <span className="block font-fell text-[13px] uppercase tracking-[0.3em] text-amber-200/70">
                  Encyclopaedia
                </span>
                <span className="text-eb-gradient block font-fell text-[clamp(3rem,7.5vw,6.5rem)] italic leading-[0.95] drop-shadow-[0_4px_30px_rgba(240,192,112,0.25)]">
                  Britannica
                </span>
                <span className="mt-1 block font-mono text-xs tracking-[0.2em] text-amber-200/60">1768 – 1860</span>
              </span>
              <span className="flex justify-center py-2 md:py-0">
                <VsMedallion size={84} />
              </span>
              <span className="md:text-left">
                <span className="block text-[13px] uppercase tracking-[0.3em] text-sky-200/70">The free encyclopedia</span>
                <span className="text-wp-gradient block text-[clamp(2.75rem,7vw,6rem)] font-semibold leading-[0.98] tracking-tight drop-shadow-[0_4px_30px_rgba(56,189,248,0.25)]">
                  Wikipedia
                </span>
                <span className="mt-1 block font-mono text-xs tracking-[0.2em] text-sky-200/70">2026 · live</span>
              </span>
            </h1>
            <p className="mt-6 max-w-2xl text-[15px] leading-relaxed text-slate-300 md:text-base">
              A scholar who has read only the <em className="font-serif text-amber-100">Encyclopaedia Britannica</em> of
              1768–1860 debates a Wikipedia editor of 2026. A moderator decides what changed:{" "}
              <span className="text-white">the words, the facts, or the worldview.</span>
            </p>
          </div>

          <EraTimeline />

          <nav className="mx-auto flex w-full max-w-3xl gap-1 rounded-2xl bg-black/35 p-1.5 ring-1 ring-white/10 backdrop-blur-md">
            {NAV.map(([key, label, sub, icon]) => {
              const on = tab === key;
              return (
                <button
                  key={key}
                  onClick={() => setTab(key)}
                  aria-current={on ? "page" : undefined}
                  className={`group flex flex-1 items-center gap-3 rounded-xl px-3 py-2.5 text-left transition duration-200 md:px-4 ${
                    on
                      ? "bg-white text-slate-900 shadow-[-8px_10px_30px_-12px_rgba(240,192,112,0.7),8px_10px_30px_-12px_rgba(56,189,248,0.7)]"
                      : "text-slate-300 hover:bg-white/10 hover:text-white"
                  }`}
                >
                  <span
                    className={`hidden h-9 w-9 shrink-0 items-center justify-center rounded-lg transition sm:inline-flex ${
                      on
                        ? "bg-gradient-to-br from-[#b4532a] via-[#5b4bc4] to-[#0ea5e9] text-white shadow"
                        : "bg-white/5 ring-1 ring-white/10 group-hover:bg-white/10"
                    }`}
                  >
                    {icon}
                  </span>
                  <span className="min-w-0">
                    <span className="block text-[15px] font-semibold">{label}</span>
                    <span className={`hidden truncate text-[11px] md:block ${on ? "text-slate-500" : "text-slate-400"}`}>
                      {sub}
                    </span>
                  </span>
                </button>
              );
            })}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-8 md:px-10 md:py-10">
        <div className={tab === "debate" ? "animate-fade-up" : "hidden"}>
          <DebateView mock={mock} />
        </div>
        <div className={tab === "ask" ? "animate-fade-up" : "hidden"}>
          <AskView mock={mock} />
        </div>
        <div className={tab === "cases" ? "animate-fade-up" : "hidden"}>
          <CasesView mock={mock} active={tab === "cases"} />
        </div>
      </main>

      <footer className="mx-auto w-full max-w-[1500px] px-6 pb-10 pt-4 md:px-10">
        <div className="mb-6 h-px bg-gradient-to-r from-transparent via-[#c99a4b]/60 to-transparent" />
        <div className="flex flex-col items-center gap-3 text-center text-xs text-slate-500">
          <div className="flex flex-wrap justify-center gap-2">
            {["Nemotron 3.5 Super VL", "Nemotron Embed VL", "Nemotron Rerank VL", "Nemotron Parse", "Hermes Agent", "LanceDB"].map(
              (t) => (
                <span key={t} className="rounded-full bg-white/70 px-2.5 py-1 font-medium text-slate-600 ring-1 ring-slate-200">
                  {t}
                </span>
              ),
            )}
          </div>
          <p className="max-w-3xl">
            Sources: Encyclopaedia Britannica 1st–8th editions (1768–1860, digitised by the National Library of Scotland)
            · Wikipedia (CC BY-SA). Agents powered by NVIDIA Nemotron via Hermes · claims fact-checked by Nemotron Rerank ·
            scans examined by Nemotron 3.5 Super VL.
          </p>
        </div>
      </footer>
    </CitationProvider>
  );
}
