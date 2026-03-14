"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import type { StockSentimentItem } from "@/hooks/use-sector-sentiment";
import { Skeleton } from "@/components/ui/skeleton";
import { CheckCircle2, XCircle } from "lucide-react";

interface SectorDetailDrawerProps {
  sectorKey: string | null;
  stocks: StockSentimentItem[];
  isLoading: boolean;
  open: boolean;
  onClose: () => void;
}

function zoneTextColor(zone: string): string {
  switch (zone) {
    case "Strong": return "text-emerald-700";
    case "Bullish": return "text-emerald-600";
    case "Neutral": return "text-slate-600";
    case "Weak": return "text-amber-600";
    case "Bear": return "text-red-600";
    default: return "text-slate-600";
  }
}

function zoneBadgeColor(zone: string): string {
  switch (zone) {
    case "Strong": return "bg-emerald-100 text-emerald-700";
    case "Bullish": return "bg-emerald-50 text-emerald-600";
    case "Neutral": return "bg-slate-100 text-slate-600";
    case "Weak": return "bg-amber-100 text-amber-700";
    case "Bear": return "bg-red-100 text-red-700";
    default: return "bg-slate-100 text-slate-600";
  }
}

function MetricPill({ label, value }: { label: string; value: boolean }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium",
      value ? "bg-emerald-50 text-emerald-700" : "bg-slate-50 text-slate-400"
    )}>
      {value ? (
        <CheckCircle2 className="h-2.5 w-2.5" />
      ) : (
        <XCircle className="h-2.5 w-2.5" />
      )}
      {label}
    </span>
  );
}

function formatSectorName(name: string): string {
  return name
    .replace(/^NIFTY\s*/i, "")
    .replace(/\bINDEX\b/i, "")
    .trim() || name;
}

export function SectorDetailDrawer({
  sectorKey,
  stocks,
  isLoading,
  open,
  onClose,
}: SectorDetailDrawerProps) {
  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full sm:max-w-lg overflow-y-auto">
        <SheetHeader className="pb-4 border-b border-slate-200">
          <SheetTitle className="text-base font-semibold text-slate-800">
            {sectorKey ? formatSectorName(sectorKey) : "Sector Detail"}
          </SheetTitle>
          <SheetDescription className="text-sm text-slate-500">
            {stocks.length} stocks sorted by sentiment score
          </SheetDescription>
        </SheetHeader>

        {isLoading ? (
          <div className="mt-4 space-y-3 px-4">
            {Array.from({ length: 8 }).map((_, i) => (
              <Skeleton key={i} className="h-16 rounded-lg" />
            ))}
          </div>
        ) : stocks.length === 0 ? (
          <div className="mt-8 text-center text-sm text-slate-400">
            No stock sentiment data for this sector.
          </div>
        ) : (
          <div className="mt-4 space-y-2 px-4">
            {stocks.map((stock, idx) => (
              <div
                key={stock.ticker}
                className="bg-white rounded-lg border border-slate-100 p-3 hover:border-slate-200 transition-colors"
              >
                {/* Header row */}
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-400 w-5">
                      {idx + 1}.
                    </span>
                    <span className="text-sm font-semibold text-slate-800 font-mono">
                      {stock.ticker}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={cn(
                      "text-lg font-bold font-mono tabular-nums",
                      zoneTextColor(stock.zone)
                    )}>
                      {stock.composite_score.toFixed(1)}
                    </span>
                    <span className={cn(
                      "rounded-full px-2 py-0.5 text-[10px] font-medium",
                      zoneBadgeColor(stock.zone)
                    )}>
                      {stock.zone}
                    </span>
                  </div>
                </div>

                {/* Key Metrics */}
                <div className="flex flex-wrap gap-1">
                  <MetricPill label="10E" value={stock.above_10ema} />
                  <MetricPill label="21E" value={stock.above_21ema} />
                  <MetricPill label="50E" value={stock.above_50ema} />
                  <MetricPill label="200E" value={stock.above_200ema} />
                  <MetricPill label="GC" value={stock.golden_cross} />
                  <MetricPill label="MACD" value={stock.macd_bull_cross} />
                  <MetricPill label="52H" value={stock.hit_52w_high} />
                </div>

                {/* RSI values */}
                {(stock.rsi_daily !== null || stock.rsi_weekly !== null) && (
                  <div className="mt-1.5 flex gap-3 text-[10px] text-slate-500">
                    {stock.rsi_daily !== null && (
                      <span>RSI(D): <span className="font-mono font-medium">{stock.rsi_daily.toFixed(1)}</span></span>
                    )}
                    {stock.rsi_weekly !== null && (
                      <span>RSI(W): <span className="font-mono font-medium">{stock.rsi_weekly.toFixed(1)}</span></span>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
