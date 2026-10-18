"use client";

import { formatArgs } from "@/utils/api";
import type { Citation, TraceStep } from "@/utils/types";
import { isVisionTool } from "@/utils/vision";
import { CitationChip } from "./citations";
import { EyeIcon, VisionCard } from "./vision";

function toolColor(name: string): string {
  if (isVisionTool(name)) return "text-violet-300";
  if (name.includes("britannica")) return "text-amber-300";
  if (name.includes("wikipedia")) return "text-sky-300";
  return "text-emerald-300";
}

/** Numbered tool-call list on a dark panel; vision steps expand into a "looked at the scan" card. */
export function TraceList({
  steps,
  citations,
  unsupported,
}: {
  steps: TraceStep[];
  citations?: Citation[];
  unsupported?: string[];
}) {
  return (
    <ol className="space-y-1.5">
      {steps.map((s, i) => {
        const vision = isVisionTool(s.name);
        return (
          <li key={i} className="flex items-start gap-3 font-mono text-[12.5px]">
            <span className="w-5 shrink-0 text-right text-slate-500">{i + 1}</span>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="min-w-0 break-words">
                  {vision && <EyeIcon className="mr-1 inline-block align-[-2px] text-violet-300" />}
                  <span className={toolColor(s.name)}>{s.name}</span>
                  <span className="text-slate-400">({formatArgs(s.args)})</span>
                </span>
                {typeof s.n_hits === "number" && !vision && (
                  <span className="rounded bg-white/10 px-1.5 font-sans text-[10.5px] font-semibold text-slate-300">
                    {s.n_hits} hit{s.n_hits === 1 ? "" : "s"}
                  </span>
                )}
                {!vision && s.cite_ids && s.cite_ids.length > 0 && (
                  <span className="flex flex-wrap gap-0.5 font-sans">
                    {s.cite_ids.slice(0, 6).map((id) => (
                      <CitationChip key={id} id={id} citations={citations} unsupported={unsupported} />
                    ))}
                    {s.cite_ids.length > 6 && (
                      <span className="self-center text-[10.5px] text-slate-500">+{s.cite_ids.length - 6}</span>
                    )}
                  </span>
                )}
              </div>
              {s.vision && (
                <div className="mt-2 mb-1 max-w-3xl">
                  <VisionCard name={s.name} args={s.args} vision={s.vision} tone="dark" />
                </div>
              )}
            </div>
          </li>
        );
      })}
      {steps.length === 0 && <li className="text-sm text-slate-500">No tool calls recorded.</li>}
    </ol>
  );
}
