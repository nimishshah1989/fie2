"use client";

import { SignalChip } from "@/components/signal-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { ChevronRight, Layers } from "lucide-react";
import type { GlobalSector } from "@/lib/global-pulse-types";

interface GlobalSectorListProps {
  sectors: GlobalSector[];
  marketName: string;
  period: string;
  selectedSector: string | null;
  onSelectSector: (key: string) => void;
  isLoading?: boolean;
}

export function GlobalSectorList({
  sectors, marketName, period, selectedSector, onSelectSector, isLoading,
}: GlobalSectorListProps) {
  const periodKey = period.toLowerCase();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-40" />
        {Array.from({ length: 6 }).map((_, i) => (
          <Skeleton key={i} className="h-14 rounded-lg" />
        ))}
      </div>
    );
  }

  if (sectors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <Layers className="size-10 text-muted-foreground/40 mb-3" />
        <p className="text-sm text-muted-foreground">No sector data available for {marketName}</p>
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <div className="flex items-center gap-2 mb-3">
        <Layers className="size-4 text-teal-600" />
        <h3 className="text-sm font-semibold text-foreground">{marketName} Sectors</h3>
        <span className="text-xs text-muted-foreground">({sectors.length})</span>
      </div>
      {sectors.map((sec) => {
        const ratioRet = sec.ratio_returns_vs_parent[periodKey];
        const absRet = sec.index_returns[periodKey];
        const isSelected = selectedSector === sec.key;

        return (
          <button
            key={sec.key}
            type="button"
            onClick={() => sec.has_stocks && onSelectSector(sec.key)}
            className={cn(
              "w-full flex items-center justify-between px-3 py-2.5 rounded-lg border transition-all text-left group",
              isSelected
                ? "border-teal-300 bg-teal-50 ring-1 ring-teal-200"
                : "border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50",
              !sec.has_stocks && "cursor-default opacity-75",
            )}
          >
            <div className="min-w-0">
              <p className="text-sm font-medium text-foreground truncate">{sec.name}</p>
              <p className="text-[11px] text-muted-foreground font-mono">
                {sec.symbol} &bull; {sec.last != null ? sec.last.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "—"}
              </p>
            </div>
            <div className="flex items-center gap-2 shrink-0">
              <div className="text-right">
                {ratioRet != null && (
                  <p className={cn(
                    "text-xs font-mono font-semibold",
                    ratioRet > 0 ? "text-emerald-600" : ratioRet < 0 ? "text-red-600" : "text-slate-500",
                  )}>
                    {ratioRet > 0 ? "+" : ""}{ratioRet.toFixed(1)}% RS
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
              <SignalChip signal={sec.signal} />
              {sec.has_stocks && (
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
  );
}
