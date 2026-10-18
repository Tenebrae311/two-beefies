"use client";

import { useRef, useState } from "react";
import { askBackend, formatArgs, loadMockAsk } from "@/utils/api";
import type { AskResponse, Citation } from "@/utils/types";
import { CitedText, SourceIcon, useCitations } from "./citations";
import { Spinner } from "./debate-parts";

const EXAMPLES = [
  "How many planets did Britannica list in 1771, and how does that compare to today?",
  "What did early Britannica editions say caused cholera?",
  "How was electricity explained in the 1797 edition versus today?",
  "How did Britannica describe Africa, and how has that framing changed?",
];

export function AskView({ mock }: { mock: boolean }) {
  const { register, open } = useCitations();
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AskResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [demoNote, setDemoNote] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);

  const ask = async (q: string) => {
    const clean = q.trim();
    if (!clean || loading) return;
    setQuestion(clean);
    setLoading(true);
    setError(null);
    setResult(null);
    setDemoNote(null);
    abort.current?.abort();
    const ctrl = new AbortController();
    abort.current = ctrl;
    try {
      let data: AskResponse;
      if (mock) {
        await new Promise((r) => setTimeout(r, 1200));
        data = await loadMockAsk();
        setDemoNote("Mock mode — showing a recorded answer.");
      } else {
        try {
          data = await askBackend(clean, ctrl.signal);
        } catch (e) {
          const status = (e as { status?: number }).status;
          if ((e as Error).name === "AbortError") return;
          // Network failure or proxy error (backend down) → recorded demo answer.
          if (status === undefined || status >= 500) {
            data = await loadMockAsk();
            setDemoNote(
              `Backend unreachable (${(e as Error).message.slice(0, 80)}) — showing a recorded demo answer instead.`,
            );
          } else throw e;
        }
      }
      register(data.citations);
      setResult(data);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  };

  const eb = result?.citations.filter((c) => c.source === "britannica") ?? [];
  const wp = result?.citations.filter((c) => c.source !== "britannica") ?? [];

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <form
        className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200"
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
      >
        <label className="mb-2 block text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">
          Ask across 250 years of encyclopaedias
        </label>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void ask(question);
          }}
          rows={3}
          placeholder="e.g. How did the understanding of combustion change between 1771 and today?"
          className="w-full resize-none rounded-xl bg-slate-50 px-4 py-3 text-lg text-slate-900 outline-none ring-1 ring-slate-200 placeholder:text-slate-400 focus:ring-2 focus:ring-amber-400"
        />
        <div className="mt-3 flex flex-wrap items-center gap-2">
          {EXAMPLES.map((ex) => (
            <button
              key={ex}
              type="button"
              onClick={() => void ask(ex)}
              disabled={loading}
              className="rounded-full bg-white px-3 py-1 text-left text-[13px] text-slate-600 ring-1 ring-slate-200 transition hover:-translate-y-px hover:bg-amber-50 hover:ring-amber-300 disabled:opacity-40"
            >
              {ex}
            </button>
          ))}
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="ml-auto inline-flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 font-semibold text-white shadow transition hover:-translate-y-px hover:shadow-lg disabled:opacity-40"
          >
            {loading ? <Spinner /> : null} Ask
            <kbd className="hidden rounded bg-white/15 px-1.5 text-[10px] font-normal sm:inline">Ctrl ↵</kbd>
          </button>
        </div>
      </form>

      {loading && (
        <div className="animate-fade-up space-y-3 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Spinner /> The Hermes agent is consulting Britannica and Wikipedia…
          </div>
          {[92, 80, 86, 55].map((w, i) => (
            <div key={i} className="relative h-3 overflow-hidden rounded bg-slate-100" style={{ width: `${w}%` }}>
              <div className="shimmer absolute inset-0" />
            </div>
          ))}
        </div>
      )}

      {error && (
        <div className="rounded-xl bg-red-50 px-4 py-3 text-sm text-red-800 ring-1 ring-red-300">
          <strong>Error:</strong> {error}
        </div>
      )}

      {result && (
        <div className="animate-fade-up space-y-5">
          {demoNote && (
            <div className="flex items-center gap-3 rounded-xl bg-amber-50 px-4 py-2.5 text-sm text-amber-900 ring-1 ring-amber-300">
              <span className="rounded bg-amber-400 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-amber-950">
                Demo
              </span>
              {demoNote}
            </div>
          )}

          <article className="rounded-2xl bg-white p-7 shadow-lg ring-1 ring-slate-200">
            <div className="mb-4 flex flex-wrap items-center gap-3">
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-400">Answer</span>
              {result.unsupported.length > 0 ? (
                <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2.5 py-0.5 text-xs font-semibold text-red-700 ring-1 ring-red-300">
                  ⚠ {result.unsupported.length} unsupported citation{result.unsupported.length === 1 ? "" : "s"}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-300">
                  ✓ All citations backed by retrieved sources
                </span>
              )}
              <span className="ml-auto text-xs text-slate-400">
                {result.citations.length} sources · {result.trace.length} tool calls
              </span>
            </div>
            <CitedText
              text={result.answer}
              citations={result.citations}
              unsupported={result.unsupported}
              className="text-[16.5px] leading-relaxed text-slate-800"
            />
          </article>

          {result.citations.length > 0 && (
            <div className="grid gap-5 md:grid-cols-2">
              <SourceList
                title="Encyclopaedia Britannica · 1768–1860"
                cites={eb}
                eb
                onOpen={(c) => open(c.cite_id, { citation: c })}
              />
              <SourceList title="Wikipedia · 2026" cites={wp} onOpen={(c) => open(c.cite_id, { citation: c })} />
            </div>
          )}

          <details className="group rounded-2xl bg-slate-900 text-slate-200 shadow ring-1 ring-slate-800">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-5 py-3 text-sm font-semibold">
              <span className="transition group-open:rotate-90">▸</span>
              Agent trace
              <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs font-normal">{result.trace.length} steps</span>
            </summary>
            <ol className="space-y-1.5 px-5 pb-4">
              {result.trace.map((s, i) => (
                <li key={i} className="flex items-start gap-3 font-mono text-[12.5px]">
                  <span className="w-5 shrink-0 text-right text-slate-500">{i + 1}</span>
                  <span>
                    <span
                      className={
                        s.name.includes("britannica")
                          ? "text-amber-300"
                          : s.name.includes("wikipedia")
                            ? "text-sky-300"
                            : "text-emerald-300"
                      }
                    >
                      {s.name}
                    </span>
                    <span className="text-slate-400">({formatArgs(s.args)})</span>
                  </span>
                </li>
              ))}
              {result.trace.length === 0 && <li className="text-sm text-slate-500">No tool calls recorded.</li>}
            </ol>
          </details>
        </div>
      )}
    </div>
  );
}

function SourceList({
  title,
  cites,
  eb = false,
  onOpen,
}: {
  title: string;
  cites: Citation[];
  eb?: boolean;
  onOpen: (c: Citation) => void;
}) {
  return (
    <div className={`rounded-2xl p-5 ring-1 ${eb ? "parchment ring-[#d8bf8c]" : "modern-grid ring-slate-200"}`}>
      <h3
        className={
          eb
            ? "mb-3 font-fell text-[13px] uppercase tracking-[0.14em] text-[#7a5230]"
            : "mb-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-slate-500"
        }
      >
        {title}
      </h3>
      {cites.length === 0 && <p className="text-sm italic opacity-60">No sources from this side.</p>}
      <ul className="space-y-2">
        {cites.map((c) => (
          <li key={c.cite_id}>
            <button
              onClick={() => onOpen(c)}
              className={`flex w-full gap-3 rounded-xl p-3 text-left transition hover:-translate-y-px hover:shadow-md ${
                eb ? "bg-[#fbf3df]/80 ring-1 ring-[#e2cd9f]" : "bg-white ring-1 ring-slate-200"
              }`}
            >
              {c.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={c.image_url}
                  alt=""
                  className="h-16 w-12 shrink-0 rounded-sm object-cover shadow ring-1 ring-black/10"
                />
              ) : (
                <SourceIcon source={c.source} className="mt-0.5" />
              )}
              <span className="min-w-0">
                <span className={`block truncate font-semibold ${eb ? "font-serif text-[16px] text-ink" : "text-slate-900"}`}>
                  {c.title}
                </span>
                <span className="block text-[11px] text-slate-500">
                  {[c.edition, c.year].filter(Boolean).join(" · ")}
                </span>
                <span className={`mt-1 line-clamp-2 text-[13px] ${eb ? "font-serif text-[#5b4128]" : "text-slate-600"}`}>
                  {c.snippet}
                </span>
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
