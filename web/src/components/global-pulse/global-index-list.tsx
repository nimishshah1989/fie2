"use client";

import { useMemo } from "react";
import { SignalChip } from "@/components/signal-chip";
import { cn } from "@/lib/utils";
import { ChevronRight } from "lucide-react";
import type { GlobalIndex } from "@/lib/global-pulse-types";

// Region flag emoji for visual grouping
const REGION_FLAGS: Record<string, string> = {
  US: "US", Europe: "EU", Asia: "AS", Americas: "AM", India: "IN",
};

const REGION_COLORS: Record<string, string> = {
  US: "bg-blue-50 text-blue-700",
  Europe: "bg-purple-50 text-purple-700",
  Asia: "bg-amber-50 text-amber-700",
  Americas: "bg-emerald-50 text-emerald-700",
  India: "bg-teal-50 text-teal-700",
};

interface GlobalIndexListProps {
  indices: GlobalIndex[];
  period: string;
  selectedIndex: string | null;
  onSelectIndex: (key: string) => void;
}

export function GlobalIndexList({ indices, period, selectedIndex, onSelectIndex }: GlobalIndexListProps) {
  const periodKey = period.toLowerCase();

  // Group by region
  const grouped = useMemo(() => {
    const map: Record<string, GlobalIndex[]> = {};
    for (const idx of indices) {
      (map[idx.region] ??= []).push(idx);
    }
    return map;
  }, [indices]);

  const regions = useMemo(() => Object.keys(grouped), [grouped]);

  return (
    <div className="space-y-4">
      {regions.map((region) => (
        <div key={region}>
          <div className="flex items-center gap-2 mb-2">
            <span className={cn("text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded", REGION_COLORS[region] || "bg-slate-100 text-slate-600")}>
              {REGION_FLAGS[region] || region}
            </span>
            <span className="text-xs text-muted-foreground">{grouped[region].length} indices</span>
          </div>
          <div className="space-y-1">
            {grouped[region].map((idx) => {
              const ratioRet = idx.ratio_returns[periodKey];
              const absRet = idx.index_returns[periodKey];
              const isSelected = selectedIndex === idx.key;

              return (
                <button
                  key={idx.key}
                  type="button"
                  onClick={() => idx.has_sectors && onSelectIndex(idx.key)}
                  className={cn(
                    "w-full flex items-center justify-between px-3 py-2.5 rounded-lg border transition-all text-left group",
                    isSelected
                      ? "border-teal-300 bg-teal-50 ring-1 ring-teal-200"
                      : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
                    !idx.has_sectors && "cursor-default opacity-75",
                  )}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate">{idx.name}</p>
                      <p className="text-[11px] text-muted-foreground font-mono">
                        {idx.last != null ? idx.last.toLocaleString("en-US", { maximumFractionDigits: 0 }) : "—"}
                        {" "}
                        <span className="text-muted-foreground/60">{idx.currency}</span>
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <div className="text-right">
                      {ratioRet != null && (
                        <p className={cn(
                          "text-xs font-mono font-semibold",
                          ratioRet > 0 ? "text-emerald-600" : ratioRet < 0 ? "text-red-600" : "text-slate-500",
                        )}>
                          {ratioRet > 0 ? "+" : ""}{ratioRet.toFixed(1)}%
                        </p>
                      )}
                      {absRet != null && (
                        <p className={cn(
                          "text-[10px] font-mono",
                          absRet > 0 ? "text-emerald-500" : absRet < 0 ? "text-red-500" : "text-slate-400",
                        )}>
                          abs {absRet > 0 ? "+" : ""}{absRet.toFixed(1)}%
                        </p>
                      )}
                    </div>
                    <SignalChip signal={idx.signal} />
                    {idx.has_sectors && (
                      <ChevronRight className={cn(
                        "size-4 text-slate-400 transition-colors",
                        isSelected && "text-teal-600",
                      )} />
                    )}
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      ))}
    </div>
  );
}
