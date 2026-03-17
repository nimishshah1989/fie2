"use client";

import { SignalChip } from "@/components/signal-chip";
import { Skeleton } from "@/components/ui/skeleton";
import { cn } from "@/lib/utils";
import { BarChart3 } from "lucide-react";
import type { GlobalStock } from "@/lib/global-pulse-types";

interface GlobalStockListProps {
  stocks: GlobalStock[];
  sectorName: string;
  parentName: string;
  period: string;
  isLoading?: boolean;
}

export function GlobalStockList({ stocks, sectorName, parentName, period, isLoading }: GlobalStockListProps) {
  const periodKey = period.toLowerCase();

  if (isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-40" />
        {Array.from({ length: 8 }).map((_, i) => (
          <Skeleton key={i} className="h-12 rounded-lg" />
        ))}
      </div>
    );
  }

  if (stocks.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center">
        <BarChart3 className="size-10 text-muted-foreground/40 mb-3" />
        <p className="text-sm text-muted-foreground">No stock data for {sectorName}</p>
      </div>
    );
  }

  return (
    <div>
      <div className="flex items-center gap-2 mb-3">
        <BarChart3 className="size-4 text-teal-600" />
        <h3 className="text-sm font-semibold text-foreground">{sectorName} Stocks</h3>
        <span className="text-xs text-muted-foreground">vs {sectorName}</span>
      </div>

      {/* Table header */}
      <div className="grid grid-cols-[1fr_80px_80px_80px_100px] gap-1 px-3 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
        <span>Stock</span>
        <span className="text-right">Price</span>
        <span className="text-right">RS Return</span>
        <span className="text-right">Abs Return</span>
        <span className="text-right">Signal</span>
      </div>

      {/* Stock rows */}
      <div className="divide-y divide-slate-50">
        {stocks.map((stock, i) => {
          const ratioRet = stock.ratio_returns[periodKey];
          const absRet = stock.index_returns[periodKey];

          return (
            <div
              key={stock.ticker}
              className="grid grid-cols-[1fr_80px_80px_80px_100px] gap-1 px-3 py-2 items-center hover:bg-slate-50 transition-colors"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{stock.ticker}</p>
                <p className="text-[10px] text-muted-foreground truncate">{stock.name}</p>
              </div>
              <p className="text-xs font-mono text-right tabular-nums">
                {stock.last != null ? stock.last.toLocaleString("en-US", { maximumFractionDigits: 2 }) : "—"}
              </p>
              <p className={cn(
                "text-xs font-mono font-semibold text-right tabular-nums",
                ratioRet != null && ratioRet > 0 ? "text-emerald-600" : ratioRet != null && ratioRet < 0 ? "text-red-600" : "text-slate-500",
              )}>
                {ratioRet != null ? `${ratioRet > 0 ? "+" : ""}${ratioRet.toFixed(1)}%` : "—"}
              </p>
              <p className={cn(
                "text-xs font-mono text-right tabular-nums",
                absRet != null && absRet > 0 ? "text-emerald-500" : absRet != null && absRet < 0 ? "text-red-500" : "text-slate-400",
              )}>
                {absRet != null ? `${absRet > 0 ? "+" : ""}${absRet.toFixed(1)}%` : "—"}
              </p>
              <div className="flex justify-end">
                <SignalChip signal={stock.signal} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
