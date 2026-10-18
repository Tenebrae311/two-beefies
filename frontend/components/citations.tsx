"use client";

import { createContext, Fragment, useCallback, useContext, useMemo, useRef, useState, type ReactNode } from "react";
import { bareId, sourceFromId } from "@/utils/api";
import { findCitation, isUnsupported, splitCitations } from "@/utils/cite";
import type { Citation } from "@/utils/types";
import { CitationDrawer } from "./CitationDrawer";

interface OpenRequest {
  id: string;
  citation?: Citation;
  unsupported: boolean;
}

interface CitationCtx {
  register: (cites: Citation[] | undefined) => void;
  lookup: (id: string) => Citation | undefined;
  open: (id: string, opts?: { citation?: Citation; unsupported?: boolean }) => void;
  offline: boolean;
  version: number;
}

const Ctx = createContext<CitationCtx | null>(null);

export function useCitations(): CitationCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error("useCitations must be used inside <CitationProvider>");
  return c;
}

export function CitationProvider({ children, offline = false }: { children: ReactNode; offline?: boolean }) {
  const registry = useRef(new Map<string, Citation>());
  const [version, bump] = useState(0);
  const [req, setReq] = useState<OpenRequest | null>(null);

  const register = useCallback((cites: Citation[] | undefined) => {
    if (!cites?.length) return;
    let changed = false;
    for (const c of cites) {
      if (!c?.cite_id) continue;
      const prev = registry.current.get(c.cite_id);
      if (!prev || (!prev.text && c.text)) {
        registry.current.set(c.cite_id, { ...prev, ...c });
        registry.current.set(bareId(c.cite_id), { ...prev, ...c });
        changed = true;
      }
    }
    if (changed) bump((n) => n + 1);
  }, []);

  const lookup = useCallback(
    (id: string) => registry.current.get(id) ?? registry.current.get(bareId(id)),
    [],
  );

  const open = useCallback(
    (id: string, opts?: { citation?: Citation; unsupported?: boolean }) => {
      setReq({ id, citation: opts?.citation ?? lookup(id), unsupported: !!opts?.unsupported });
    },
    [lookup],
  );

  const value = useMemo(
    () => ({ register, lookup, open, offline, version }),
    [register, lookup, open, offline, version],
  );

  return (
    <Ctx.Provider value={value}>
      {children}
      {req && (
        <CitationDrawer
          key={req.id}
          citeId={req.id}
          initial={req.citation}
          unsupported={req.unsupported}
          offline={offline}
          onClose={() => setReq(null)}
        />
      )}
    </Ctx.Provider>
  );
}

/* ------------------------------------------------------------------ */

export function SourceIcon({ source, className = "" }: { source: Citation["source"] | null; className?: string }) {
  if (source === "britannica")
    return (
      <span
        className={`inline-flex h-4 min-w-4 items-center justify-center rounded-[3px] bg-[#7a2e12] px-[3px] font-fell text-[10px] leading-none text-amber-50 ${className}`}
      >
        EB
      </span>
    );
  return (
    <span
      className={`inline-flex h-4 min-w-4 items-center justify-center rounded-[3px] bg-slate-800 px-[3px] font-serif text-[11px] font-semibold leading-none text-white ${className}`}
    >
      W
    </span>
  );
}

function shortLabel(c: Citation | undefined, id: string): string {
  if (c?.title) {
    const t = c.title.length > 26 ? c.title.slice(0, 24).trimEnd() + "…" : c.title;
    return c.source === "britannica" && c.year ? `${t} · ${c.year}` : t;
  }
  const b = bareId(id);
  return b.length > 18 ? b.slice(0, 16) + "…" : b;
}

export function CitationChip({
  id,
  citations,
  unsupported,
}: {
  id: string;
  citations?: Citation[];
  unsupported?: string[];
}) {
  const { lookup, open } = useCitations();
  const c = findCitation(id, citations) ?? lookup(id);
  const bad = isUnsupported(id, unsupported);
  const source = c?.source ?? sourceFromId(id);

  const base =
    "group/chip relative mx-0.5 inline-flex max-w-[16rem] translate-y-[-1px] items-center gap-1 rounded-full px-1.5 py-[1px] align-middle font-sans text-[11px] font-medium leading-4 ring-1 transition-all hover:-translate-y-[2px] hover:shadow-md cursor-pointer";
  const tone = bad
    ? "bg-red-50 text-red-700 ring-red-400 hover:bg-red-100"
    : source === "britannica"
      ? "bg-[#f6e6c4] text-[#5b3410] ring-[#c9a46a] hover:bg-[#f1dcae]"
      : "bg-slate-100 text-slate-700 ring-slate-300 hover:bg-white";

  return (
    <button
      type="button"
      onClick={(e) => {
        e.stopPropagation();
        open(id, { citation: c, unsupported: bad });
      }}
      className={`${base} ${tone}`}
      aria-label={bad ? "not backed by any retrieved source" : (c?.title ?? id)}
      data-unsupported={bad || undefined}
    >
      {bad ? (
        <svg viewBox="0 0 16 16" className="h-3 w-3 shrink-0 fill-current" aria-hidden>
          <path d="M8 1.5 15 14H1L8 1.5Zm0 4a.75.75 0 0 0-.75.75v3.5a.75.75 0 0 0 1.5 0v-3.5A.75.75 0 0 0 8 5.5Zm0 6.75a.9.9 0 1 0 0-1.8.9.9 0 0 0 0 1.8Z" />
        </svg>
      ) : (
        <SourceIcon source={source} className="scale-90" />
      )}
      <span className="truncate">{shortLabel(c, id)}</span>
      <span
        role="tooltip"
        className={`pointer-events-none absolute bottom-full left-1/2 z-30 mb-2 hidden w-64 -translate-x-1/2 rounded-lg px-3 py-2 text-left text-[11.5px] font-normal leading-snug shadow-xl group-hover/chip:block ${
          bad ? "bg-red-700 text-white" : "bg-slate-900 text-slate-100"
        }`}
      >
        {bad ? (
          <>
            <strong className="block font-semibold">Not backed by any retrieved source</strong>
            <span className="opacity-80">The agent cited {id} but never retrieved it — possible hallucination.</span>
          </>
        ) : (
          <>
            <strong className="block font-semibold">{c?.title ?? id}</strong>
            {c?.snippet && <span className="line-clamp-3 opacity-80">{c.snippet}</span>}
          </>
        )}
      </span>
    </button>
  );
}

/* ---------------------------- rich text ---------------------------- */

function renderInline(text: string, keyBase: string, citations?: Citation[], unsupported?: string[]): ReactNode[] {
  const nodes: ReactNode[] = [];
  splitCitations(text).forEach((seg, i) => {
    if (seg.kind === "cite") {
      nodes.push(<CitationChip key={`${keyBase}-c${i}`} id={seg.id} citations={citations} unsupported={unsupported} />);
      return;
    }
    // **bold** and *italic* (very small markdown subset)
    const parts = seg.text.split(/(\*\*[^*]+\*\*|\*[^*\n]+\*)/g);
    parts.forEach((p, j) => {
      if (!p) return;
      if (p.startsWith("**") && p.endsWith("**") && p.length > 4)
        nodes.push(
          <strong key={`${keyBase}-${i}-${j}`} className="font-semibold">
            {p.slice(2, -2)}
          </strong>,
        );
      else if (p.startsWith("*") && p.endsWith("*") && p.length > 2)
        nodes.push(<em key={`${keyBase}-${i}-${j}`}>{p.slice(1, -1)}</em>);
      else nodes.push(<Fragment key={`${keyBase}-${i}-${j}`}>{p}</Fragment>);
    });
  });
  return nodes;
}

export function CitedText({
  text,
  citations,
  unsupported,
  streaming,
  dropCap,
  className = "",
}: {
  text: string;
  citations?: Citation[];
  unsupported?: string[];
  streaming?: boolean;
  dropCap?: boolean;
  className?: string;
}) {
  const blocks = text
    .replace(/\r\n/g, "\n")
    .split(/\n{2,}/)
    .map((b) => b.trim())
    .filter(Boolean);

  return (
    <div className={`space-y-3 ${className}`}>
      {blocks.map((block, bi) => {
        const isLast = bi === blocks.length - 1;
        const lines = block.split("\n");
        const isList = lines.every((l) => /^\s*([-*•]|\d+[.)])\s+/.test(l));
        if (isList) {
          return (
            <ul key={bi} className={`ml-4 list-disc space-y-1 marker:opacity-50 ${streaming && isLast ? "caret" : ""}`}>
              {lines.map((l, li) => (
                <li key={li}>{renderInline(l.replace(/^\s*([-*•]|\d+[.)])\s+/, ""), `${bi}-${li}`, citations, unsupported)}</li>
              ))}
            </ul>
          );
        }
        const heading = block.match(/^#{1,4}\s+(.*)$/);
        if (heading && lines.length === 1)
          return (
            <p key={bi} className="font-semibold">
              {renderInline(heading[1], `${bi}`, citations, unsupported)}
            </p>
          );
        return (
          <p
            key={bi}
            className={`${dropCap && bi === 0 ? "drop-cap" : ""} ${streaming && isLast ? "caret" : ""}`}
          >
            {lines.map((l, li) => (
              <Fragment key={li}>
                {li > 0 && <br />}
                {renderInline(l, `${bi}-${li}`, citations, unsupported)}
              </Fragment>
            ))}
          </p>
        );
      })}
      {blocks.length === 0 && streaming && <p className="caret opacity-60" />}
    </div>
  );
}
