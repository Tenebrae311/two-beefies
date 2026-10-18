"use client";

import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { formatArgs } from "@/utils/api";
import { parseModerator } from "@/utils/cite";
import { summarizeTurnEvidence } from "@/utils/evidence";
import type { Role, VerdictPoint } from "@/utils/types";
import { useDebate, type Turn } from "@/utils/useDebate";
import { isVisionTool, pendingToolLabel } from "@/utils/vision";
import { useCitations } from "./citations";
import { AgreementMeter, ModeratorCard, Spinner, TurnBubble, VerdictCard } from "./debate-parts";
import { FightCard, prefersReducedMotion } from "./duel";
import { SwordsIcon, VsMedallion } from "./flair";
import { EyeIcon } from "./vision";

const PRESETS = ["Astronomy", "Electricity", "Africa", "Cholera", "Combustion"];

export function DebateView({ mock }: { mock: boolean }) {
  const { register } = useCitations();
  const { state, runLive, runMock, stop } = useDebate(register);
  const [topic, setTopic] = useState("Astronomy");
  const [presets, setPresets] = useState(PRESETS);
  /* the ≈2 s fight-card intro shown on top while the debate already starts underneath */
  const [intro, setIntro] = useState<{ key: number; topic: string } | null>(null);
  const closeIntro = useCallback(() => setIntro(null), []);

  /* live mode: offer the headwords of the pages that are actually indexed */
  useEffect(() => {
    if (mock) return;
    fetch("/api/topics")
      .then((r) => (r.ok ? r.json() : []))
      .then((t: unknown) => {
        if (Array.isArray(t) && t.length) setPresets(t.map(String));
      })
      .catch(() => {});
  }, [mock]);

  const running = state.status === "running" || state.status === "connecting";

  const start = (t: string) => {
    const clean = t.trim();
    if (!clean) return;
    setTopic(clean);
    if (!prefersReducedMotion()) setIntro({ key: Date.now(), topic: clean });
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

  /* evidence: the verdict's own summary, else aggregate the per-turn reranker events */
  const verdictEvidence = useMemo(
    () => (state.verdict ? (state.verdict.evidence ?? summarizeTurnEvidence(state.turns)) : null),
    [state.verdict, state.turns],
  );

  /* per-side reranker support, for the balance scale */
  const sideSupport = useMemo(
    () => verdictEvidence ?? summarizeTurnEvidence(state.turns),
    [verdictEvidence, state.turns],
  );

  /* the reranker scores a debater's turn right after turn_end: show "checking…" on the latest one meanwhile */
  const latestKey = useMemo(() => {
    const out: Partial<Record<Role, string>> = {};
    for (const t of state.turns) out[t.role] = t.key;
    return out;
  }, [state.turns]);
  const awaitingEvidence = (t: Turn) => running && t.evidence === undefined && latestKey[t.role] === t.key;

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
      {intro && <FightCard key={intro.key} topic={intro.topic} onDone={closeIntro} />}
      {/* ------------------------------ topic bar ------------------------------ */}
      <div className="glass-card rounded-3xl p-4 ring-1 ring-slate-200/80 md:p-5">
        <div className="mb-3 flex items-baseline gap-3 px-1">
          <h2 className="text-duel-gradient text-xl font-semibold tracking-tight md:text-2xl">Choose the battleground</h2>
          <span className="hidden text-sm text-slate-500 sm:inline">One topic, two centuries apart.</span>
        </div>
        <form
          className="flex flex-col gap-3 md:flex-row md:items-center"
          onSubmit={(e) => {
            e.preventDefault();
            start(topic);
          }}
        >
          <label className="flex flex-1 items-center gap-3 rounded-2xl bg-white px-4 py-3 shadow-inner ring-1 ring-slate-200 transition focus-within:ring-2 focus-within:ring-amber-400">
            <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Topic</span>
            <input
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Astronomy, Electricity, Cholera…"
              className="flex-1 bg-transparent text-xl font-medium text-slate-900 outline-none placeholder:text-slate-400"
            />
          </label>
          {running ? (
            <button
              type="button"
              onClick={stop}
              className="inline-flex items-center justify-center gap-2 rounded-2xl bg-slate-200 px-6 py-3.5 font-semibold text-slate-800 transition hover:bg-slate-300"
            >
              <span className="h-2.5 w-2.5 rounded-sm bg-slate-700" /> Stop
            </button>
          ) : (
            <button
              type="submit"
              className="btn-duel inline-flex items-center justify-center gap-2 rounded-2xl px-7 py-3.5 text-[15px] font-semibold text-white"
            >
              <SwordsIcon /> Start the debate
            </button>
          )}
        </form>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="mr-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Try</span>
          {presets.map((p) => (
            <button
              key={p}
              type="button"
              disabled={running}
              onClick={() => start(p)}
              className={`rounded-full px-3 py-1 text-sm font-medium ring-1 transition disabled:opacity-40 ${
                state.topic === p
                  ? "bg-gradient-to-r from-[#7a2e12] to-[#1e3a8a] text-white shadow ring-transparent"
                  : "bg-white/80 text-slate-700 ring-slate-200 hover:-translate-y-0.5 hover:bg-gradient-to-r hover:from-amber-50 hover:to-sky-50 hover:shadow-md hover:ring-amber-300"
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
      <div className="duel-frame rounded-3xl">
        {/* headers + meter */}
        <div className="grid overflow-hidden rounded-t-[22px] lg:grid-cols-[1fr_minmax(280px,360px)_1fr]">
          <SideHeader role="britannica" turns={state.turns} running={running} />
          <div className="scoreboard flex flex-col items-center justify-center gap-2 px-6 py-5">
            <div className="text-center text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-400">
              {state.topic ? (
                <>
                  Debating <span className="text-amber-300">{state.topic}</span>
                </>
              ) : (
                "No debate yet"
              )}
            </div>
            <AgreementMeter
              points={meterPoints}
              pending={running}
              ebSupport={sideSupport?.britannica ?? null}
              wpSupport={sideSupport?.wikipedia ?? null}
            />
          </div>
          <SideHeader role="wikipedia" turns={state.turns} running={running} />
        </div>

        {/* body */}
        <div className="relative min-h-[420px] rounded-b-[22px]">
          <div className="pointer-events-none absolute inset-0 grid grid-cols-1 overflow-hidden rounded-b-[22px] md:grid-cols-2">
            <div className="parchment" />
            <div className="modern-grid hidden md:block" />
            {/* the time rift between the eras; the moderator rules from it */}
            <div className="rift absolute inset-y-0 left-1/2 hidden w-[3px] -translate-x-1/2 md:block" />
            <div className="rift-spark absolute left-1/2 hidden h-16 w-[5px] -translate-x-1/2 rounded-full bg-white/90 blur-[2px] md:block" />
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
                  <div className="h-px flex-1 bg-gradient-to-r from-transparent to-[#b58a4c]/70" />
                  <span className="relative rounded-full bg-[#0c0b12] p-[1.5px] shadow-lg">
                    <span className="absolute inset-0 rounded-full bg-gradient-to-r from-[#f0c070] via-[#818cf8] to-[#38bdf8]" />
                    <span className="relative flex items-center gap-2 rounded-full bg-[#0c0b12] px-4 py-1 text-[11px] font-semibold uppercase tracking-[0.24em] text-white">
                      <span className="text-amber-300">✦</span>
                      Round <span className="font-fell text-[15px] normal-case tracking-normal">{roman(round)}</span>
                      <span className="text-sky-300">✦</span>
                    </span>
                  </span>
                  <div className="h-px flex-1 bg-gradient-to-l from-transparent to-sky-400/70" />
                </div>
                <div className="grid grid-cols-1 gap-6 md:grid-cols-2 md:gap-10">
                  <div className="space-y-4">
                    {r.eb.map((t) => (
                      <TurnBubble key={t.key} turn={t} awaitingEvidence={awaitingEvidence(t)} />
                    ))}
                  </div>
                  <div className="space-y-4">
                    {r.wp.map((t) => (
                      <TurnBubble key={t.key} turn={t} awaitingEvidence={awaitingEvidence(t)} />
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

      {state.verdict && <VerdictCard verdict={state.verdict} evidence={verdictEvidence} />}
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
  if (active && pendingTool && isVisionTool(pendingTool.name)) {
    status = (
      <>
        <span className="inline-flex h-4 w-4 shrink-0 animate-pulse items-center justify-center rounded-full bg-violet-600 text-white">
          <EyeIcon className="!h-2.5 !w-2.5" />
        </span>
        <span className="truncate text-[11.5px] font-medium">
          {pendingToolLabel(pendingTool.name, eb)} <span className="opacity-60">(Nemotron VL)</span>
        </span>
      </>
    );
  } else if (active && pendingTool) {
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
      className={`relative flex h-16 w-16 shrink-0 items-center justify-center rounded-full text-[28px] ${
        eb
          ? "bg-gradient-to-br from-[#9a3f17] to-[#4a1a08] font-fell text-amber-100 shadow-[0_8px_24px_-6px_rgba(154,63,23,0.7)] ring-4 ring-[#f0c070]/60"
          : "bg-gradient-to-br from-white to-sky-50 font-serif font-semibold text-slate-900 shadow-[0_8px_24px_-6px_rgba(14,165,233,0.6)] ring-4 ring-sky-300/60"
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
    <div className="relative grid min-h-[340px] grid-cols-1 gap-6 py-10 md:grid-cols-2 md:gap-10">
      <div className="absolute left-1/2 top-1/2 z-10 hidden -translate-x-1/2 -translate-y-1/2 md:block">
        <VsMedallion size={72} />
      </div>
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <span aria-hidden className="h-12 font-fell text-8xl leading-none text-[#b4532a]/35">“</span>
        <p className="max-w-sm font-serif text-2xl italic leading-relaxed text-[#6b4a26]">
          “Name your subject, and I shall answer from the learning of the age.”
        </p>
        <p className="text-xs uppercase tracking-[0.16em] text-[#9a7a52]">Sees only Britannica, 1768–1860</p>
      </div>
      <div className="flex flex-col items-center justify-center gap-3 text-center">
        <span aria-hidden className="flex h-12 items-center font-mono text-5xl leading-none text-sky-400/45">{"</>"}</span>
        <p className="max-w-sm text-xl leading-relaxed text-slate-600">
          Pick a topic and I&apos;ll check it against the current consensus — with citations.
        </p>
        <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-400">Sees only Wikipedia, 2026</p>
      </div>
    </div>
  );
}

function roman(n: number) {
  return ["", "I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"][n] ?? String(n);
}
