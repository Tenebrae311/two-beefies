"use client";

import { Fragment, useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { imageSource, VISION_MODEL_LABEL, visionTitle } from "@/utils/vision";
import type { VisionResult } from "@/utils/types";
import { CitationChip, SourceIcon } from "./citations";

type Tone = "eb" | "wp" | "light" | "dark";

export function EyeIcon({ className = "" }: { className?: string }) {
  return (
    <svg viewBox="0 0 20 20" className={`h-3.5 w-3.5 fill-current ${className}`} aria-hidden>
      <path d="M10 4c4.2 0 7.3 3 8.6 5.4a1.3 1.3 0 0 1 0 1.2C17.3 13 14.2 16 10 16s-7.3-3-8.6-5.4a1.3 1.3 0 0 1 0-1.2C2.7 7 5.8 4 10 4Zm0 2.2a3.8 3.8 0 1 0 0 7.6 3.8 3.8 0 0 0 0-7.6Zm0 1.9a1.9 1.9 0 1 1 0 3.8 1.9 1.9 0 0 1 0-3.8Z" />
    </svg>
  );
}

const CARD_TONE: Record<Tone, { card: string; head: string; q: string; a: string; thumb: string; muted: string }> = {
  eb: {
    card: "border-[#c9a46a] bg-[#f6ead0] text-[#3b2a1a] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.5)]",
    head: "text-[#7a2e12]",
    q: "text-[#5b3410]",
    a: "text-[#3b2a1a]",
    thumb: "bg-[#e9d6ac] ring-[#c9a46a]",
    muted: "text-[#7a5230]",
  },
  wp: {
    card: "border-sky-200 bg-sky-50/70 text-slate-800",
    head: "text-sky-800",
    q: "text-slate-600",
    a: "text-slate-800",
    thumb: "bg-white ring-slate-200",
    muted: "text-slate-500",
  },
  light: {
    card: "border-slate-200 bg-white text-slate-800",
    head: "text-slate-800",
    q: "text-slate-600",
    a: "text-slate-800",
    thumb: "bg-slate-50 ring-slate-200",
    muted: "text-slate-500",
  },
  dark: {
    card: "border-white/10 bg-white/[0.04] text-slate-200",
    head: "text-violet-200",
    q: "text-slate-400",
    a: "text-slate-100",
    thumb: "bg-slate-800 ring-white/10",
    muted: "text-slate-400",
  },
};

function imageLabel(url: string, i: number, n: number, compare: boolean): string {
  const src = compare && n === 2 ? (i === 0 ? "britannica" : "wikipedia") : imageSource(url);
  return src === "britannica" ? "Britannica scan" : "Wikipedia image";
}

/**
 * "👁 Looked at the original scan" — what the vision model was asked about the page image(s) and what it saw.
 * Used inside debate turns (eb/wp tone), the Ask trace (dark) and the case viewer (light).
 */
export function VisionCard({
  name,
  args,
  vision,
  tone = "light",
}: {
  name: string;
  args?: Record<string, unknown>;
  vision: VisionResult;
  tone?: Tone;
}) {
  const t = CARD_TONE[tone];
  const compare = name === "compare_images";
  const [zoom, setZoom] = useState<number | null>(null);
  const [broken, setBroken] = useState<Record<number, boolean>>({});
  const [more, setMore] = useState(false);
  const long = vision.answer.length > 340;

  const citeIds = [args?.cite_id, args?.britannica_cite_id, args?.wikipedia_cite_id].filter(
    (x): x is string => typeof x === "string" && !!x,
  );
  const labels = vision.images.map((u, i) => imageLabel(u, i, vision.images.length, compare));
  /* the edition year of the Britannica page ("EB:1771-v1-p489" → 1771), for the specimen tags */
  const ebYear = citeIds.map((id) => id.match(/\b(1[78]\d\d)\b/)?.[1]).find(Boolean) ?? null;

  return (
    <figure className={`animate-fade-up rounded-xl border font-sans ${t.card}`}>
      <figcaption className="flex flex-wrap items-center gap-x-2 gap-y-1 px-3 pt-2.5">
        <span className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-violet-600 text-white shadow-sm">
          <EyeIcon className="!h-3 !w-3" />
        </span>
        <span className={`text-[12.5px] font-semibold ${t.head}`}>{visionTitle(name)}</span>
        <span className="inline-flex items-center gap-1 rounded-full bg-slate-900 px-1.5 py-px text-[9.5px] font-semibold text-white">
          <span className="h-1.5 w-1.5 rounded-full bg-[#76b900]" /> {VISION_MODEL_LABEL}
        </span>
        <span className="ml-auto flex flex-wrap gap-0.5">
          {citeIds.map((id) => (
            <CitationChip key={id} id={id} />
          ))}
        </span>
      </figcaption>

      <div className="flex flex-col gap-3 p-3 sm:flex-row">
        {vision.images.length > 0 && (
          <div className="flex shrink-0 items-start gap-2">
            {vision.images.map((src, i) => {
              const isEB = labels[i] === "Britannica scan";
              return (
                <Fragment key={src + i}>
                  {compare && i > 0 && (
                    <span className="mt-12 inline-flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-gradient-to-r from-[#b4532a] via-violet-500 to-sky-500 text-[13px] font-bold text-white shadow-md">
                      ↔
                    </span>
                  )}
                  <Specimen
                    src={src}
                    alt={labels[i]}
                    eb={isEB}
                    tag={`${isEB ? "Plate" : "Wikipedia"} · ${isEB ? (ebYear ?? "EB") : "2026"}`}
                    thumb={t.thumb}
                    broken={!!broken[i]}
                    onBroken={() => setBroken((b) => ({ ...b, [i]: true }))}
                    onOpen={() => setZoom(i)}
                  />
                </Fragment>
              );
            })}
          </div>
        )}
        <div className="min-w-0 flex-1 space-y-1.5">
          {vision.question && (
            <p className={`text-[12px] leading-snug ${t.q}`}>
              <span className="mr-1 rounded bg-black/10 px-1 text-[9.5px] font-bold uppercase tracking-wider">
                Asked
              </span>
              <span className="italic">{vision.question}</span>
            </p>
          )}
          <div className={`text-[12.5px] leading-snug ${t.a}`}>
            <span className="mr-1 rounded bg-violet-600/90 px-1 text-[9.5px] font-bold uppercase tracking-wider text-white">
              Saw
            </span>
            <span className={`whitespace-pre-wrap ${long && !more ? "line-clamp-5" : ""}`}>{vision.answer || "—"}</span>
            {long && (
              <button
                type="button"
                onClick={() => setMore((m) => !m)}
                className={`mt-0.5 block text-[11px] font-semibold underline-offset-2 hover:underline ${t.muted}`}
              >
                {more ? "Show less" : "Show full answer"}
              </button>
            )}
          </div>
        </div>
      </div>

      {zoom !== null && vision.images[zoom] && (
        <Lightbox
          images={vision.images}
          labels={labels}
          index={zoom}
          caption={vision.question}
          onIndex={setZoom}
          onClose={() => setZoom(null)}
        />
      )}
    </figure>
  );
}

/** A scan presented like a specimen: tagged, and a magnifying lens follows the cursor on hover. */
function Specimen({
  src,
  alt,
  eb,
  tag,
  thumb,
  broken,
  onBroken,
  onOpen,
}: {
  src: string;
  alt: string;
  eb: boolean;
  tag: string;
  thumb: string;
  broken: boolean;
  onBroken: () => void;
  onOpen: () => void;
}) {
  const [lens, setLens] = useState<{ x: number; y: number } | null>(null);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const W = 88;
  const H = 120;
  const PAD = 4;
  const Z = 3;
  /* where the object-cover / object-top image actually sits inside the thumb */
  const cover = natural ? Math.max(W / natural.w, H / natural.h) : 1;
  const rw = natural ? natural.w * cover : W;
  const rh = natural ? natural.h * cover : H;
  const offX = (W - rw) / 2;
  return (
    <span className="relative flex flex-col items-center gap-1">
      <button
        type="button"
        onClick={onOpen}
        title="Hover to magnify · click to enlarge"
        onMouseMove={(e) => {
          const r = e.currentTarget.getBoundingClientRect();
          setLens({ x: e.clientX - r.left, y: e.clientY - r.top });
        }}
        onMouseLeave={() => setLens(null)}
        className={`relative cursor-zoom-in overflow-hidden rounded-md p-1 shadow-md ring-1 transition hover:-translate-y-0.5 hover:shadow-lg ${thumb}`}
        style={{ width: W + 8, height: H + 8 }}
      >
        {broken ? (
          <span className="flex h-full w-full items-center justify-center text-center text-[10px] opacity-60">
            image unavailable
          </span>
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            src={src}
            alt={alt}
            onError={onBroken}
            onLoad={(e) => {
              const im = e.currentTarget;
              if (im.naturalWidth && im.naturalHeight) setNatural({ w: im.naturalWidth, h: im.naturalHeight });
            }}
            className={`h-full w-full rounded-sm object-cover object-top ${eb ? "sepia-[.25]" : ""}`}
          />
        )}
        <span className="absolute inset-x-1 bottom-1 flex items-center gap-1 rounded-b-sm bg-black/60 px-1 py-0.5 text-[9px] font-semibold text-white">
          <SourceIcon source={eb ? "britannica" : "wikipedia"} className="scale-75" />
          <span className="truncate">{eb ? "Britannica" : "Wikipedia"}</span>
        </span>
      </button>
      {lens && !broken && (
        <span
          aria-hidden
          className="lens pointer-events-none absolute z-30 h-24 w-24 rounded-full bg-white bg-no-repeat"
          style={{
            left: lens.x - 48,
            top: lens.y - 48,
            backgroundImage: `url("${src}")`,
            backgroundSize: `${rw * Z}px ${rh * Z}px`,
            backgroundPosition: `${48 - (lens.x - PAD - offX) * Z}px ${48 - (lens.y - PAD) * Z}px`,
            filter: eb ? "sepia(0.25)" : undefined,
          }}
        />
      )}
      <span
        className={`whitespace-nowrap rounded-sm px-1.5 py-px font-mono text-[9.5px] font-semibold uppercase tracking-[0.12em] ${
          eb ? "bg-[#7a2e12] text-amber-50" : "bg-slate-900 text-sky-100"
        }`}
      >
        {tag}
      </span>
    </span>
  );
}

function Lightbox({
  images,
  labels,
  index,
  caption,
  onIndex,
  onClose,
}: {
  images: string[];
  labels: string[];
  index: number;
  caption?: string;
  onIndex: (i: number) => void;
  onClose: () => void;
}) {
  const n = images.length;
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight" && n > 1) onIndex((index + 1) % n);
      if (e.key === "ArrowLeft" && n > 1) onIndex((index - 1 + n) % n);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [index, n, onClose, onIndex]);

  // Portal: debate bubbles keep a CSS transform from their entry animation, which would trap position:fixed.
  return createPortal(
    <div
      className="animate-fade-in fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/85 p-4 backdrop-blur-sm md:p-10"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
    >
      <figure className="flex max-h-full max-w-5xl flex-col items-center gap-3" onClick={(e) => e.stopPropagation()}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={images[index]}
          alt={labels[index]}
          className={`max-h-[80vh] max-w-full rounded-md bg-white object-contain shadow-2xl ring-1 ring-white/20 ${
            labels[index] === "Britannica scan" ? "sepia-[.2]" : ""
          }`}
        />
        <figcaption className="flex flex-wrap items-center justify-center gap-3 text-center text-sm text-slate-200">
          <span className="rounded-full bg-white/10 px-2.5 py-0.5 text-xs font-semibold ring-1 ring-white/20">
            {labels[index]}
            {n > 1 && ` · ${index + 1}/${n}`}
          </span>
          {caption && <span className="max-w-2xl italic text-slate-300">“{caption}”</span>}
          <a
            href={images[index]}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-slate-400 underline-offset-2 hover:text-white hover:underline"
          >
            Open original ↗
          </a>
        </figcaption>
      </figure>
      {n > 1 && (
        <>
          <button
            type="button"
            aria-label="Previous image"
            onClick={(e) => {
              e.stopPropagation();
              onIndex((index - 1 + n) % n);
            }}
            className="absolute left-3 top-1/2 -translate-y-1/2 rounded-full bg-white/10 px-3 py-2 text-xl text-white ring-1 ring-white/20 hover:bg-white/20"
          >
            ‹
          </button>
          <button
            type="button"
            aria-label="Next image"
            onClick={(e) => {
              e.stopPropagation();
              onIndex((index + 1) % n);
            }}
            className="absolute right-3 top-1/2 -translate-y-1/2 rounded-full bg-white/10 px-3 py-2 text-xl text-white ring-1 ring-white/20 hover:bg-white/20"
          >
            ›
          </button>
        </>
      )}
      <button
        type="button"
        onClick={onClose}
        aria-label="Close"
        className="absolute right-4 top-4 rounded-full bg-white/10 p-2 text-white ring-1 ring-white/20 hover:bg-white/20"
      >
        <svg viewBox="0 0 20 20" className="h-5 w-5 fill-current">
          <path d="M5.3 4.3a1 1 0 0 1 1.4 0L10 7.6l3.3-3.3a1 1 0 1 1 1.4 1.4L11.4 9l3.3 3.3a1 1 0 0 1-1.4 1.4L10 10.4l-3.3 3.3a1 1 0 0 1-1.4-1.4L8.6 9 5.3 5.7a1 1 0 0 1 0-1.4Z" />
        </svg>
      </button>
    </div>,
    document.body,
  );
}
