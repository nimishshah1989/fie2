"use client";

import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import type { SentimentMetric } from "@/lib/types";

interface StockListDrawerProps {
  metric: SentimentMetric | null;
  open: boolean;
  onClose: () => void;
}

export function StockListDrawer({ metric, open, onClose }: StockListDrawerProps) {
  if (!metric) return null;

  const tickers = metric.tickers ?? [];

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader className="pb-4 border-b border-slate-200">
          <SheetTitle className="text-base font-semibold text-foreground">
            {metric.label}
          </SheetTitle>
          <SheetDescription className="text-sm text-muted-foreground">
            {metric.count} of {metric.total} stocks ({metric.pct.toFixed(1)}%)
          </SheetDescription>
        </SheetHeader>

        {tickers.length > 0 ? (
          <div className="mt-4 px-4 grid grid-cols-3 gap-1.5">
            {tickers.map((ticker) => (
              <div
                key={ticker}
                className="text-xs font-mono bg-slate-50 rounded px-2 py-1.5 text-slate-700 text-center truncate"
                title={ticker}
              >
                {ticker}
              </div>
            ))}
          </div>
        ) : (
          <div className="mt-8 text-center text-sm text-slate-400">
            No ticker data available. Try refreshing the sentiment data.
          </div>
        )}
      </SheetContent>
    </Sheet>
  );
}
