"use client";

import { useCallback, useEffect, useReducer, useRef } from "react";
import { BACKEND_URL, loadMockDebate, sleep } from "./api";
import type { Citation, DebateEvent, Role, Verdict } from "./types";

export interface ToolActivity {
  name: string;
  args: Record<string, unknown>;
  hits?: Citation[];
  done: boolean;
}

export interface Turn {
  key: string;
  role: Role;
  round: number;
  text: string;
  finished: boolean;
  citations: Citation[];
  unsupported: string[];
  tools: ToolActivity[];
}

export type DebateStatus = "idle" | "connecting" | "running" | "done" | "error";

export interface DebateState {
  status: DebateStatus;
  topic: string;
  turns: Turn[];
  verdict: Verdict | null;
  error?: string;
  mode: "live" | "mock";
  fallbackReason?: string;
  lastRound: number;
}

type Action =
  | { kind: "start"; topic: string; mode: "live" | "mock"; fallbackReason?: string }
  | { kind: "event"; ev: DebateEvent }
  | { kind: "fail"; message: string }
  | { kind: "stop" };

const initial: DebateState = { status: "idle", topic: "", turns: [], verdict: null, mode: "live", lastRound: 0 };

let turnSeq = 0;

function lastOpenTurnIdx(turns: Turn[], role: Role): number {
  for (let i = turns.length - 1; i >= 0; i--) {
    if (turns[i].role === role) return turns[i].finished ? -1 : i;
  }
  return -1;
}

function newTurn(role: Role, round: number): Turn {
  return {
    key: `t${++turnSeq}`,
    role,
    round,
    text: "",
    finished: false,
    citations: [],
    unsupported: [],
    tools: [],
  };
}

function reducer(state: DebateState, action: Action): DebateState {
  switch (action.kind) {
    case "start":
      return {
        ...initial,
        status: "connecting",
        topic: action.topic,
        mode: action.mode,
        fallbackReason: action.fallbackReason,
      };
    case "fail":
      return { ...state, status: "error", error: action.message };
    case "stop":
      return {
        ...state,
        status: state.status === "running" || state.status === "connecting" ? "done" : state.status,
        turns: state.turns.map((t) => (t.finished ? t : { ...t, finished: true })),
      };
    case "event":
      break;
  }

  const ev = action.ev;
  const s: DebateState = { ...state, status: state.status === "connecting" ? "running" : state.status };
  const turns = [...s.turns];

  const ensureOpen = (role: Role, round?: number): number => {
    let idx = lastOpenTurnIdx(turns, role);
    if (idx === -1) {
      turns.push(newTurn(role, round ?? Math.max(1, s.lastRound)));
      idx = turns.length - 1;
    }
    return idx;
  };

  switch (ev.type) {
    case "turn_start": {
      // Close any dangling open turn for this role
      const prev = lastOpenTurnIdx(turns, ev.role);
      if (prev !== -1) turns[prev] = { ...turns[prev], finished: true };
      turns.push(newTurn(ev.role, ev.round));
      return { ...s, turns, lastRound: Math.max(s.lastRound, ev.round) };
    }
    case "token": {
      const i = ensureOpen(ev.role);
      turns[i] = { ...turns[i], text: turns[i].text + (ev.text ?? "") };
      return { ...s, turns };
    }
    case "tool_call": {
      const i = ensureOpen(ev.role);
      turns[i] = { ...turns[i], tools: [...turns[i].tools, { name: ev.name, args: ev.args ?? {}, done: false }] };
      return { ...s, turns };
    }
    case "tool_result": {
      const i = ensureOpen(ev.role);
      const tools = [...turns[i].tools];
      let ti = -1;
      for (let k = tools.length - 1; k >= 0; k--) {
        if (!tools[k].done && tools[k].name === ev.name) {
          ti = k;
          break;
        }
      }
      if (ti === -1) for (let k = tools.length - 1; k >= 0; k--) if (!tools[k].done) { ti = k; break; }
      if (ti === -1) tools.push({ name: ev.name, args: {}, hits: ev.hits ?? [], done: true });
      else tools[ti] = { ...tools[ti], hits: ev.hits ?? [], done: true };
      turns[i] = { ...turns[i], tools };
      return { ...s, turns };
    }
    case "turn_end": {
      let i = lastOpenTurnIdx(turns, ev.role);
      if (i === -1) {
        turns.push(newTurn(ev.role, ev.round));
        i = turns.length - 1;
      }
      turns[i] = {
        ...turns[i],
        round: ev.round ?? turns[i].round,
        text: ev.text ?? turns[i].text,
        citations: ev.citations ?? [],
        unsupported: ev.unsupported ?? [],
        tools: turns[i].tools.map((t) => (t.done ? t : { ...t, done: true })),
        finished: true,
      };
      return { ...s, turns, lastRound: Math.max(s.lastRound, ev.round ?? 0) };
    }
    case "verdict":
      return {
        ...s,
        verdict: { converged: !!ev.converged, points: ev.points ?? [], summary: ev.summary ?? "" },
      };
    case "done":
      return { ...s, status: "done", turns: turns.map((t) => (t.finished ? t : { ...t, finished: true })) };
    case "error":
      return { ...s, status: "error", error: ev.message };
    default:
      return s;
  }
}

/** Chop a finished text into small token deltas, to emulate streaming in mock replays. */
function* fakeTokens(text: string): Generator<string> {
  const words = text.split(/(\s+)/);
  let buf = "";
  let n = 0;
  for (const w of words) {
    buf += w;
    if (/\S/.test(w)) n++;
    if (n >= 3) {
      yield buf;
      buf = "";
      n = 0;
    }
  }
  if (buf) yield buf;
}

export function useDebate(onCitations: (c: Citation[] | undefined) => void) {
  const [state, dispatch] = useReducer(reducer, initial);
  const runId = useRef(0);
  const esRef = useRef<EventSource | null>(null);
  const onCitesRef = useRef(onCitations);
  useEffect(() => {
    onCitesRef.current = onCitations;
  }, [onCitations]);

  const emit = useCallback((ev: DebateEvent) => {
    if (ev.type === "tool_result") onCitesRef.current(ev.hits);
    if (ev.type === "turn_end") onCitesRef.current(ev.citations);
    dispatch({ kind: "event", ev });
  }, []);

  const closeStream = useCallback(() => {
    esRef.current?.close();
    esRef.current = null;
  }, []);

  const runMock = useCallback(
    async (topic: string, fallbackReason?: string) => {
      closeStream();
      const my = ++runId.current;
      dispatch({ kind: "start", topic, mode: "mock", fallbackReason });
      let events: DebateEvent[];
      try {
        events = await loadMockDebate();
      } catch {
        dispatch({ kind: "fail", message: "Could not load mock-debate.json" });
        return;
      }
      const sawTokens: Partial<Record<string, boolean>> = {};
      for (const ev of events) {
        if (runId.current !== my) return;
        await sleep(ev.type === "token" ? 40 : 300);
        if (runId.current !== my) return;
        if (ev.type === "turn_start") sawTokens[ev.role] = false;
        if (ev.type === "token") sawTokens[ev.role] = true;
        if (ev.type === "turn_end" && ev.role !== "moderator" && !sawTokens[ev.role] && ev.text) {
          for (const chunk of fakeTokens(ev.text)) {
            if (runId.current !== my) return;
            emit({ type: "token", role: ev.role, text: chunk });
            await sleep(28);
          }
          await sleep(250);
        }
        if (ev.type === "turn_start" && ev.role === "moderator") await sleep(400);
        emit(ev);
      }
    },
    [closeStream, emit],
  );

  const runLive = useCallback(
    (topic: string) => {
      closeStream();
      const my = ++runId.current;
      dispatch({ kind: "start", topic, mode: "live" });
      let opened = false;
      let received = 0;
      let finished = false;
      const es = new EventSource(`${BACKEND_URL}/api/debate?topic=${encodeURIComponent(topic)}`);
      esRef.current = es;
      es.onopen = () => {
        opened = true;
      };
      es.onmessage = (msg) => {
        if (runId.current !== my) return;
        let ev: DebateEvent;
        try {
          ev = JSON.parse(msg.data) as DebateEvent;
        } catch {
          return;
        }
        received++;
        emit(ev);
        if (ev.type === "done" || ev.type === "error") {
          finished = true;
          es.close();
        }
      };
      es.onerror = () => {
        if (runId.current !== my || finished) return;
        es.close();
        if (!opened && received === 0) {
          // Backend unreachable → fall back to the recorded demo.
          void runMock(topic, `Backend at ${BACKEND_URL} is unreachable — replaying a recorded “Astronomy” debate.`);
        } else {
          dispatch({ kind: "fail", message: "The debate stream was interrupted." });
        }
      };
    },
    [closeStream, emit, runMock],
  );

  const stop = useCallback(() => {
    runId.current++;
    closeStream();
    dispatch({ kind: "stop" });
  }, [closeStream]);

  useEffect(() => () => closeStream(), [closeStream]);

  return { state, runLive, runMock, stop };
}
