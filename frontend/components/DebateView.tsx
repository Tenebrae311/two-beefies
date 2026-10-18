"use client";

import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { formatArgs } from "@/utils/api";
import { parseModerator } from "@/utils/cite";
import type { Role, VerdictPoint } from "@/utils/types";
import { useDebate, type Turn } from "@/utils/useDebate";
import { useCitations } from "./citations";
import { AgreementMeter, ModeratorCard, Spinner, TurnBubble, VerdictCard } from "./debate-parts";

const PRESETS = ["Astronomy", "Electricity", "Africa", "Cholera", "Combustion"];

export function DebateView({ mock }: { mock: boolean }) {
  const { register } = useCitations();
  const { state, runLive, runMock, stop } = useDebate(register);
  const [topic, setTopic] = useState("Astronomy");

  const running = state.status === "running" || state.status === "connecting";

  const start = (t: string) => {
    const clean = t.trim();
    if (!clean) return;
    setTopic(clean);
    if (mock) void runMock(clean);
    else runLive(clean);
  };

  /* ?topic=… auto-starts a debate (handy for demos: /?mock=1&topic=Astronomy) */
  const startRef = useRef(start);
  useEffect(() => {
    startRef.current = start;
  });
  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get("topic");
    if (!t) return;
    const id = setTimeout(() => startRef.current(t), 300);
    return () => clearTimeout(id);
  }, []);

  /* group turns into rounds */
  const rounds = useMemo(() => {
    const map = new Map<number, { eb: Turn[]; wp: Turn[]; mod: Turn[] }>();
    for (const t of state.turns) {
      const r = map.get(t.round) ?? { eb: [], wp: [], mod: [] };
      (t.role === "britannica" ? r.eb : t.role === "wikipedia" ? r.wp : r.mod).push(t);
      map.set(t.round, r);
    }
    return [...map.entries()].sort((a, b) => a[0] - b[0]);
  }, [state.turns]);

  /* agreement: verdict first, else the latest moderator ruling with points */
  const meterPoints: VerdictPoint[] | undefined = useMemo(() => {
    if (state.verdict?.points?.length) return state.verdict.points;
    for (let i = state.turns.length - 1; i >= 0; i--) {
      const t = state.turns[i];
      if (t.role === "moderator" && t.finished) {
        const r = parseModerator(t.text);
        if (r?.points?.length) return r.points;
      }
    }
    return undefined;
  }, [state.turns, state.verdict]);

  /* auto-follow the conversation while it is running */
  const follow = useRef(true);
  useEffect(() => {
    const onWheel = (e: WheelEvent) => {
      if (e.deltaY < 0) follow.current = false;
    };
    const onScroll = () => {
      const dist = document.documentElement.scrollHeight - window.innerHeight - window.scrollY;
      if (dist < 120) follow.current = true;
    };
    window.addEventListener("wheel", onWheel, { passive: true });
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => {
      window.removeEventListener("wheel", onWheel);
      window.removeEventListener("scroll", onScroll);
    };
  }, []);
  useEffect(() => {
    if (!running && !state.verdict) return;
    if (!follow.current) return;
    const id = requestAnimationFrame(() =>
      window.scrollTo({ top: document.documentElement.scrollHeight, behavior: "smooth" }),
    );
    return () => cancelAnimationFrame(id);
  }, [state.turns, state.verdict, running]);

  return (
    <div className="space-y-6">
      {/* ------------------------------ topic bar ------------------------------ */}
      <div className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
        <form
          className="flex flex-col gap-3 md:flex-row md:items-center"
          onSubmit={(e) => {
            e.preventDefault();
            start(topic);
          }}
        >
          <label className="flex flex-1 items-center gap-3 rounded-xl bg-slate-50 px-4 py-2.5 ring-1 ring-slate-200 focus-within:ring-2 focus-within:ring-amber-400">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Topic</span>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Astronomy, Electricity, Cholera…"
              className="flex-1 bg-transparent text-lg font-medium text-slate-900 outline-none placeholder:text-slate-400"
            />
          </label>
          {running ? (
            <button
              type="button"
              onClick={stop}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-slate-200 px-5 py-3 font-semibold text-slate-800 transition hover:bg-slate-300"
            >
              <span className="h-2.5 w-2.5 rounded-sm bg-slate-700" /> Stop
            </button>
          ) : (
            <button
              type="submit"
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#7a2e12] via-[#9a5a24] to-slate-800 px-6 py-3 font-semibold text-white shadow-lg shadow-amber-900/20 transition hover:-translate-y-px hover:shadow-xl"
            >
              Start the debate →
            </button>
          )}
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-xs text-slate-400">Try:</span>
          {PRESETS.map((p) => (
            <button
              key={p}
              type="button"
              disabled={running}
              onClick={() => start(p)}
              className={`rounded-full px-3 py-1 text-sm font-medium ring-1 transition disabled:opacity-40 ${
                state.topic === p
                  ? "bg-slate-900 text-white ring-slate-900"
                  : "bg-white text-slate-700 ring-slate-200 hover:-translate-y-px hover:bg-amber-50 hover:ring-amber-300"
              }`}
            >
              {p}
            </button>
          ))}
        </div>
      </div>

      {state.mode === "mock" && state.status !== "idle" && (
        <div className="animate-fade-up flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-900 ring-1 ring-amber-300">
          <span className="rounded bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-950">
            Demo
          </span>
          {state.fallbackReason ??
            `Mock mode — replaying a recorded “Astronomy” debate${
              state.topic && state.topic.toLowerCase() !== "astronomy" ? ` (requested topic: “${state.topic}”)` : ""
            }.`}
        </div>
      )}
      {state.status === "error" && (
        <div className="animate-fade-up rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-300">
          <strong>Debate error:</strong> {state.error}
        </div>
      )}

      {/* ------------------------------ arena ------------------------------ */}
      <div className="rounded-3xl shadow-xl ring-1 ring-slate-300/70">
        {/* headers + meter */}
        <div className="grid overflow-hidden rounded-t-3xl lg:grid-cols-[1fr_minmax(280px,360px)_1fr]">
          <SideHeader role="britannica" turns={state.turns} running={running} />
          <div className="flex flex-col justify-center gap-2 bg-slate-900 px-6 py-5">
            <div className="text-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">
              {state.topic ? (
                <>
                  Debating <span className="text-amber-300">{state.topic}</span>
                </>
              ) : (
                "No debate yet"
              )}
            </div>
            <AgreementMeter points={meterPoints} pending={running} />
          </div>
          <SideHeader role="wikipedia" turns={state.turns} running={running} />
        </div>

        {/* body */}
        <div className="relative min-h-[420px] rounded-b-3xl">
          <div className="pointer-events-none absolute inset-0 grid grid-cols-1 overflow-hidden rounded-b-3xl md:grid-cols-2">
            <div className="parchment" />
            <div className="modern-grid hidden border-l border-slate-200 md:block" />
          </div>

          <div className="relative space-y-8 px-5 py-8 md:px-8">
            {state.status === "idle" && <EmptyArena />}
            {state.status === "connecting" && (
              <div className="flex items-center justify-center gap-2 py-16 text-slate-600">
                <Spinner /> Summoning the scholar and the editor…
              </div>
            )}

            {rounds.map(([round, r]) => (
              <section key={round} className="space-y-5">
                <div className="flex items-center gap-4">
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[#b58a4c]/50" />
                  <span className="rounded-full bg-slate-900 px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.2em] text-white shadow">
                    Round {round}
                  </span>
                  <div className="h-px flex-1 bg-gradient-to-l from-transparent to-slate-400/50" />
                </div>
                <div className="grid gap-6 md:grid-cols-2 md:gap-10">
                  <div className="space-y-4">
                    {r.eb.map((t) => (
                      <TurnBubble key={t.key} turn={t} />
                    ))}
                  </div>
                  <div className="space-y-4">
                    {r.wp.map((t) => (
                      <TurnBubble key={t.key} turn={t} />
                    ))}
                  </div>
                </div>
                {r.mod.map((t) => (
                  <ModeratorCard key={t.key} turn={t} />
                ))}
              </section>
            ))}

            {state.status === "done" && !state.verdict && state.turns.length > 0 && (
              <div className="text-center text-sm italic text-slate-500">The debate has ended.</div>
            )}
          </div>
        </div>
      </div>

      {state.verdict && <VerdictCard verdict={state.verdict} />}
    </div>
  );
}

/* ---------------------------------------------------------------------- */

function SideHeader({ role, turns, running }: { role: Role; turns: Turn[]; running: boolean }) {
  const eb = role === "britannica";
  let last: Turn | undefined;
  for (let i = turns.length - 1; i >= 0; i--)
    if (turns[i].role === role) {
      last = turns[i];
      break;
    }
  const active = last && !last.finished;
  const pendingTool = last?.tools.findLast((t) => !t.done);

  let status: ReactNode;
  if (active && pendingTool) {
    status = (
      <>
        <Spinner />
        <span className="truncate font-mono text-[11px]">
          {eb ? "consulting the archives" : "searching"}: {pendingTool.name}({formatArgs(pendingTool.args)})
        </span>
      </>
    );
  } else if (active) {
    status = (
      <>
        <span className={`h-2 w-2 animate-pulse rounded-full ${eb ? "bg-[#7a2e12]" : "bg-sky-500"}`} />
        {eb ? "composing a reply…" : "typing…"}
      </>
    );
  } else if (running) {
    status = (
      <>
        <span className="h-2 w-2 rounded-full bg-slate-400" />
        listening
      </>
    );
  } else {
    status = (
      <>
        <span className="h-2 w-2 rounded-full bg-slate-300" />
        {last ? "rests the case" : "ready"}
      </>
    );
  }

  return (
    <div
      className={`flex items-center gap-4 px-6 py-5 ${
        eb ? "parchment border-b border-[#d8bf8c]" : "modern-grid flex-row-reverse border-b border-slate-200 text-right"
      }`}
    >
      <Avatar role={role} active={!!active} />
      <div className="min-w-0 flex-1">
        <div
          className={
            eb
              ? "font-fell text-[11px] uppercase tracking-[0.18em] text-[#7a5230]"
              : "text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500"
          }
        >
          {eb ? "Encyclopaedia Britannica · 1768–1860" : "Wikipedia · 2026"}
        </div>
        <div className={eb ? "font-fell text-[26px] leading-tight text-ink" : "text-[22px] font-semibold tracking-tight text-slate-900"}>
          {eb ? "The Britannica Scholar" : "The Wikipedia Editor"}
        </div>
        <div
          className={`mt-1 flex items-center gap-2 text-xs ${eb ? "text-[#7a5230]" : "justify-end text-slate-500"}`}
        >
          {status}
        </div>
      </div>
    </div>
  );
}

function Avatar({ role, active }: { role: Role; active: boolean }) {
  const eb = role === "britannica";
  return (
    <div
      className={`relative flex h-14 w-14 shrink-0 items-center justify-center rounded-full text-2xl shadow-md ${
        eb
          ? "bg-[#7a2e12] font-fell text-amber-100 ring-4 ring-[#e8d6ae]"
          : "bg-white font-serif font-semibold text-slate-900 ring-4 ring-slate-200"
      }`}
    >
      {eb ? "Æ" : "W"}
      {active && (
        <span
          className={`absolute inset-0 animate-ping rounded-full ${eb ? "bg-[#c9a46a]/40" : "bg-sky-400/30"}`}
        />
      )}
    </div>
  );
}

function EmptyArena() {
  return (
    <div className="grid gap-6 py-10 md:grid-cols-2 md:gap-10">
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <p className="max-w-sm font-serif text-xl italic leading-relaxed text-[#6b4a26]">
          “Name your subject, and I shall answer from the learning of the age.”
        </p>
        <p className="text-xs uppercase tracking-[0.16em] text-[#9a7a52]">Sees only Britannica, 1768–1860</p>
      </div>
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <p className="max-w-sm text-lg leading-relaxed text-slate-600">
          Pick a topic and I&apos;ll check it against the current consensus — with citations.
        </p>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Sees only Wikipedia, 2026</p>
      </div>
    </div>
  );
}
