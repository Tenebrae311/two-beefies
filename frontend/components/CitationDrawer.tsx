"use client";

import { useEffect, useState } from "react";
import { bareId, fetchMockSource, fetchSource, sourceFromId } from "@/utils/api";
import type { Citation } from "@/utils/types";
import { SourceIcon } from "./citations";

export function CitationDrawer({
  citeId,
  initial,
  unsupported,
  offline,
  onClose,
}: {
  citeId: string;
  initial?: Citation;
  unsupported: boolean;
  offline: boolean;
  onClose: () => void;
}) {
  const [full, setFull] = useState<Citation | null>(null);
  const [loading, setLoading] = useState(!initial?.text);
  const [zoom, setZoom] = useState(false);
  const [imgError, setImgError] = useState(false);

  useEffect(() => {
    if (initial?.text) return;
    const ctrl = new AbortController();
    const id = initial?.cite_id ?? citeId;
    const load = offline
      ? fetchMockSource(id)
      : fetchSource(id, ctrl.signal).then((c) => c ?? fetchMockSource(id));
    load.then((c) => {
      if (ctrl.signal.aborted) return;
      setFull(c);
      setLoading(false);
    });
    return () => ctrl.abort();
  }, [citeId, initial, offline]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  const c: Partial<Citation> = { ...initial, ...(full ?? {}) };
  const source = c.source ?? sourceFromId(citeId);
  const isEB = source === "britannica";
  const body = c.text || c.snippet || "";

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      <div className="animate-fade-in absolute inset-0 bg-slate-950/40 backdrop-blur-[2px]" onClick={onClose} />
      <aside
        className={`animate-slide-in relative flex h-full w-full max-w-xl flex-col shadow-2xl ${
          isEB ? "parchment text-ink" : "bg-white text-slate-900"
        }`}
      >
        <header
          className={`flex items-start gap-3 border-b px-6 py-5 ${isEB ? "border-[#d8bf8c]" : "border-slate-200"}`}
        >
          <div className="min-w-0 flex-1">
            <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 font-semibold ring-1 ${
                  isEB ? "bg-[#7a2e12] text-amber-50 ring-[#5b210c]" : "bg-slate-900 text-white ring-slate-900"
                }`}
              >
                <SourceIcon source={source} className="!bg-transparent" />
                {isEB ? "Encyclopaedia Britannica" : "Wikipedia"}
              </span>
              {c.edition && (
                <span className="rounded-full bg-black/5 px-2 py-0.5 font-medium">{c.edition}</span>
              )}
              {c.year && <span className="rounded-full bg-black/5 px-2 py-0.5 font-medium">{c.year}</span>}
              <code className="rounded bg-black/5 px-1.5 py-0.5 font-mono text-[10.5px] opacity-70">{citeId}</code>
            </div>
            <h2 className={`text-2xl leading-tight ${isEB ? "font-fell" : "font-semibold tracking-tight"}`}>
              {c.title ?? bareId(citeId)}
            </h2>
          </div>
          <button
            onClick={onClose}
            className="rounded-full p-2 text-current opacity-60 transition hover:bg-black/5 hover:opacity-100"
            aria-label="Close"
          >
            <svg viewBox="0 0 20 20" className="h-5 w-5 fill-current">
              <path d="M5.3 4.3a1 1 0 0 1 1.4 0L10 7.6l3.3-3.3a1 1 0 1 1 1.4 1.4L11.4 9l3.3 3.3a1 1 0 0 1-1.4 1.4L10 10.4l-3.3 3.3a1 1 0 0 1-1.4-1.4L8.6 9 5.3 5.7a1 1 0 0 1 0-1.4Z" />
            </svg>
          </button>
        </header>

        <div className="scrollbar-thin flex-1 space-y-5 overflow-y-auto px-6 py-5">
          {unsupported && (
            <div className="flex gap-3 rounded-xl border border-red-300 bg-red-50 p-3 text-sm text-red-800">
              <svg viewBox="0 0 16 16" className="mt-0.5 h-4 w-4 shrink-0 fill-current">
                <path d="M8 1.5 15 14H1L8 1.5Zm0 4a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 8 5.5Zm0 6.75a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8Z" />
              </svg>
              <div>
                <strong className="block">Not backed by any retrieved source</strong>
                The agent cited <code className="font-mono">{citeId}</code> without having retrieved it during the
                debate. Treat this claim as a possible hallucination.
              </div>
            </div>
          )}

          {c.image_url && !imgError && (
            <figure className="group">
              <div
                className={`relative overflow-hidden rounded-lg border shadow-lg ${
                  isEB ? "border-[#c9a46a] bg-[#e9d6ac] p-2" : "border-slate-200 bg-slate-50 p-2"
                }`}
              >
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={c.image_url}
                  alt={`Scanned page: ${c.title ?? citeId}`}
                  onError={() => setImgError(true)}
                  onClick={() => setZoom((z) => !z)}
                  className={`mx-auto w-full cursor-zoom-in rounded-sm object-contain transition-all duration-300 ${
                    zoom ? "max-h-none cursor-zoom-out" : "max-h-[46vh]"
                  } ${isEB ? "sepia-[.25]" : ""}`}
                />
              </div>
              <figcaption className="mt-2 flex items-center justify-between text-xs opacity-70">
                <span>{isEB ? "Scanned page from the original edition" : "Image"} · click to {zoom ? "shrink" : "enlarge"}</span>
                <a href={c.image_url} target="_blank" rel="noreferrer" className="underline-offset-2 hover:underline">
                  Open full scan ↗
                </a>
              </figcaption>
            </figure>
          )}

          <section>
            <h3 className="mb-2 flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.14em] opacity-60">
              {c.text ? "Full text" : "Excerpt"}
              {loading && (
                <span className="inline-flex items-center gap-1 normal-case tracking-normal">
                  <span className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent" />
                  loading full text…
                </span>
              )}
            </h3>
            {body ? (
              <div
                className={`whitespace-pre-wrap rounded-lg ${
                  isEB
                    ? "font-serif text-[17px] leading-relaxed"
                    : "bg-slate-50 p-4 text-[14.5px] leading-relaxed text-slate-700 ring-1 ring-slate-200"
                }`}
              >
                {body}
              </div>
            ) : (
              <p className="text-sm italic opacity-60">
                {loading ? "Fetching source…" : "No text available for this citation."}
              </p>
            )}
          </section>
        </div>

        {c.url && (
          <footer
            className={`flex items-center gap-3 border-t px-6 py-4 ${isEB ? "border-[#d8bf8c]" : "border-slate-200"}`}
          >
            <a
              href={c.url}
              target="_blank"
              rel="noreferrer"
              className={`inline-flex shrink-0 items-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold shadow-sm transition hover:-translate-y-px hover:shadow ${
                isEB ? "bg-[#7a2e12] text-amber-50" : "bg-slate-900 text-white"
              }`}
            >
              View original source ↗
            </a>
            <span className="min-w-0 truncate text-xs opacity-60">{c.url}</span>
          </footer>
        )}
      </aside>
    </div>
  );
}
