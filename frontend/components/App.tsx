"use client";

import { useState, useSyncExternalStore } from "react";
import { BACKEND_URL, isMockRequested } from "@/utils/api";
import { AskView } from "./AskView";
import { CitationProvider } from "./citations";
import { DebateView } from "./DebateView";

type Tab = "debate" | "ask";

const noopSubscribe = () => () => {};

export function App() {
  const mock = useSyncExternalStore(noopSubscribe, isMockRequested, () => false);
  const [tab, setTab] = useState<Tab>("debate");

  return (
    <CitationProvider offline={mock}>
      <header className="header-glow relative overflow-hidden text-white">
        <div className="mx-auto flex max-w-[1500px] flex-col gap-5 px-6 pb-0 pt-7 md:px-10">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <div className="mb-1 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-amber-200/70">
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-[#76b900]" />
                NVIDIA Nemotron Challenge
              </div>
              <h1 className="text-3xl font-semibold tracking-tight md:text-[40px] md:leading-[1.1]">
                Knowledge Across Time{" "}
                <span className="font-normal text-white/40">—</span>{" "}
                <span className="font-fell font-normal italic text-amber-100">Britannica</span>{" "}
                <span className="font-normal text-white/60">vs.</span> Wikipedia
              </h1>
              <p className="mt-2 max-w-2xl text-[15px] text-slate-300">
                A scholar who has read only the <em>Encyclopaedia Britannica</em> of 1768–1860 debates a Wikipedia
                editor of 2026. A moderator decides what changed: the words, the facts, or the worldview.
              </p>
            </div>
            <div className="flex items-center gap-2 rounded-full bg-white/5 px-3 py-1.5 text-xs text-slate-300 ring-1 ring-white/10">
              <span className={`h-2 w-2 rounded-full ${mock ? "bg-amber-400" : "bg-emerald-400"}`} />
              {mock ? "Mock mode (recorded demo)" : `Live · ${BACKEND_URL.replace(/^https?:\/\//, "")}`}
            </div>
          </div>

          <nav className="flex gap-1">
            {(
              [
                ["debate", "Debate", "Two agents argue across time"],
                ["ask", "Ask", "One agent, both encyclopaedias"],
              ] as const
            ).map(([key, label, sub]) => (
              <button
                key={key}
                onClick={() => setTab(key)}
                className={`group relative rounded-t-xl px-5 pb-3 pt-2.5 text-left transition ${
                  tab === key ? "bg-[var(--background)] text-slate-900" : "text-slate-300 hover:bg-white/5 hover:text-white"
                }`}
              >
                <span className="block text-[15px] font-semibold">{label}</span>
                <span className={`block text-[11px] ${tab === key ? "text-slate-500" : "text-slate-400"}`}>{sub}</span>
              </button>
            ))}
          </nav>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 md:px-10 md:py-8">
        <div className={tab === "debate" ? "" : "hidden"}>
          <DebateView mock={mock} />
        </div>
        <div className={tab === "ask" ? "" : "hidden"}>
          <AskView mock={mock} />
        </div>
      </main>

      <footer className="mx-auto w-full max-w-[1500px] px-6 pb-8 pt-2 text-center text-xs text-slate-400 md:px-10">
        Sources: Encyclopaedia Britannica 1st–8th editions (1768–1860, digitised by the National Library of Scotland) ·
        Wikipedia (CC BY-SA). Agents powered by NVIDIA Nemotron via Hermes.
      </footer>
    </CitationProvider>
  );
}
