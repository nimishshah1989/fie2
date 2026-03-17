"use client";

import { cn } from "@/lib/utils";
import type { GlobalIndex } from "@/lib/global-pulse-types";

const REGION_COLORS: Record<string, string> = {
  US: "border-blue-300",
  Europe: "border-purple-300",
  Asia: "border-amber-300",
  Americas: "border-emerald-300",
  India: "border-teal-300",
};

function getIntensity(value: number | null): string {
  if (value == null) return "bg-slate-100 text-slate-400";
  if (value > 10) return "bg-emerald-600 text-white";
  if (value > 5) return "bg-emerald-500 text-white";
  if (value > 2) return "bg-emerald-400 text-white";
  if (value > 0) return "bg-emerald-100 text-emerald-800";
  if (value > -2) return "bg-red-100 text-red-800";
  if (value > -5) return "bg-red-400 text-white";
  if (value > -10) return "bg-red-500 text-white";
  return "bg-red-600 text-white";
}

interface GlobalHeatmapProps {
  indices: GlobalIndex[];
  period: string;
  onSelect: (key: string) => void;
}

export function GlobalHeatmap({ indices, period, onSelect }: GlobalHeatmapProps) {
  const periodKey = period.toLowerCase();

  // Summary counts
  const bull = indices.filter((i) => (i.ratio_returns[periodKey] ?? 0) > 0).length;
  const bear = indices.filter((i) => (i.ratio_returns[periodKey] ?? 0) < 0).length;
  const neutral = indices.length - bull - bear;

  return (
    <div>
      <div className="flex items-center gap-4 mb-3">
        <p className="text-xs font-medium text-foreground">Global RS Heatmap</p>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="text-emerald-600 font-semibold">{bull} Bull</span>
          <span className="text-slate-500">{neutral} Neutral</span>
          <span className="text-red-600 font-semibold">{bear} Bear</span>
        </div>
      </div>
      <div className="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-7 lg:grid-cols-10 gap-1.5">
        {indices.map((idx) => {
          const val = idx.ratio_returns[periodKey] ?? null;
          return (
            <button
              key={idx.key}
              type="button"
              onClick={() => idx.has_sectors && onSelect(idx.key)}
              className={cn(
                "rounded-lg px-2 py-2 text-center transition-all border-l-2",
                getIntensity(val),
                REGION_COLORS[idx.region] || "border-slate-300",
                idx.has_sectors ? "cursor-pointer hover:ring-1 hover:ring-teal-300" : "cursor-default",
              )}
              title={`${idx.name}: ${val != null ? `${val > 0 ? "+" : ""}${val.toFixed(1)}%` : "N/A"} RS (${period})`}
            >
              <p className="text-[10px] font-medium truncate leading-tight">{idx.key}</p>
              <p className="text-xs font-mono font-bold mt-0.5">
                {val != null ? `${val > 0 ? "+" : ""}${val.toFixed(1)}%` : "—"}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
}
