"use client";

import { cn, getRelativeSignal } from "@/lib/utils";
import { TOP_25_SET } from "@/lib/constants";
import type { LiveIndex } from "@/lib/types";

interface SignalHeatmapProps {
  indices: LiveIndex[];
  period: string;
}

const BULL_SIGNALS = new Set(["BULLISH", "STRONG OW", "OVERWEIGHT"]);
const BEAR_SIGNALS = new Set(["BEARISH", "STRONG UW", "UNDERWEIGHT"]);

/** Returns Tailwind classes based on signal + magnitude of ratio return */
function getIntensityStyle(ratioReturn: number | null, signal: string): string {
  if (signal === "BASE") return "bg-blue-100 text-blue-700 border-blue-300";
  if (ratioReturn == null) return "bg-slate-100 text-slate-600 border-slate-300";

  const abs = Math.abs(ratioReturn);

  if (ratioReturn >= 0) {
    // Green gradient based on positive return magnitude
    if (abs >= 10) return "bg-emerald-400 text-white border-emerald-500";
    if (abs >= 7) return "bg-emerald-300 text-emerald-900 border-emerald-400";
    if (abs >= 4) return "bg-emerald-200 text-emerald-900 border-emerald-300";
    if (abs >= 2) return "bg-emerald-100 text-emerald-800 border-emerald-300";
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else {
    // Red gradient based on negative return magnitude
    if (abs >= 10) return "bg-red-400 text-white border-red-500";
    if (abs >= 7) return "bg-red-300 text-red-900 border-red-400";
    if (abs >= 4) return "bg-red-200 text-red-900 border-red-300";
    if (abs >= 2) return "bg-red-100 text-red-800 border-red-300";
    return "bg-red-50 text-red-700 border-red-200";
  }
}

function getShortName(name: string): string {
  return name.replace(/^NIFTY\s+/i, "");
}

export function SignalHeatmap({ indices, period }: SignalHeatmapProps) {
  const pk = period.toLowerCase();

  function getPeriodSignal(idx: LiveIndex): string {
    if (idx.signal === "BASE") return "BASE";
    const ratioReturn = idx.ratio_returns?.[pk] ?? null;
    if (ratioReturn == null) return "NEUTRAL";
    return getRelativeSignal(1 + ratioReturn / 100);
  }

  // Filter to only TOP_25 indices
  const top25 = indices.filter((idx) => {
    const name = idx.nse_name || idx.index_name;
    return TOP_25_SET.has(name);
  });

  // Count signals
  const bullCount = top25.filter((i) => BULL_SIGNALS.has(getPeriodSignal(i))).length;
  const bearCount = top25.filter((i) => BEAR_SIGNALS.has(getPeriodSignal(i))).length;
  const neutralCount = top25.length - bullCount - bearCount;

  if (top25.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      <h3 className="text-sm font-semibold text-foreground">
        Top 25 Signal Overview
      </h3>

      {/* Heatmap grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-2">
        {top25.map((idx) => {
          const name = idx.nse_name || idx.index_name;
          const ratioReturn = idx.ratio_returns?.[pk] ?? null;
          const periodSignal = getPeriodSignal(idx);
          const style = getIntensityStyle(ratioReturn, periodSignal);

          return (
            <button
              key={name}
              type="button"
              className={cn(
                "rounded-lg border px-2 py-2 text-center transition-shadow hover:shadow-md hover:scale-[1.03] cursor-pointer",
                style
              )}
              title={`${name} — ${periodSignal} · ${ratioReturn != null ? (ratioReturn >= 0 ? "+" : "") + ratioReturn.toFixed(1) + "%" : "N/A"} · Click to scroll`}
              onClick={() => {
                const id = `idx-${name.replace(/\s+/g, "-")}`;
                const el = document.getElementById(id);
                if (el) {
                  el.scrollIntoView({ behavior: "smooth", block: "center" });
                  el.classList.add("ring-2", "ring-blue-400");
                  setTimeout(() => el.classList.remove("ring-2", "ring-blue-400"), 2000);
                }
              }}
            >
              <div className="text-xs font-medium leading-tight">{getShortName(name)}</div>
              {ratioReturn != null && (
                <div className="text-[10px] font-mono mt-0.5 opacity-80">
                  {ratioReturn >= 0 ? "+" : ""}{ratioReturn.toFixed(1)}%
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Summary counts */}
      <div className="flex items-center gap-4 text-xs text-muted-foreground">
        <span>
          <span className="inline-block size-2 rounded-full bg-emerald-500 mr-1" />
          Bull: {bullCount}
        </span>
        <span className="text-muted-foreground/40">|</span>
        <span>
          <span className="inline-block size-2 rounded-full bg-red-500 mr-1" />
          Bear: {bearCount}
        </span>
        <span className="text-muted-foreground/40">|</span>
        <span>
          <span className="inline-block size-2 rounded-full bg-slate-400 mr-1" />
          Neutral: {neutralCount}
        </span>
      </div>
    </div>
  );
}
