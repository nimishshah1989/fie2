"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";
import { CheckCircle2, XCircle, ArrowLeft } from "lucide-react";
import { Skeleton } from "@/components/ui/skeleton";
import type { SentimentMetric, TickerWithScore } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface StockSentimentDetail {
  ticker: string;
  sector_index: string | null;
  date: string;
  composite_score: number;
  zone: string;
  metrics: {
    above_10ema: boolean;
    above_21ema: boolean;
    above_50ema: boolean;
    above_200ema: boolean;
    golden_cross: boolean;
    rsi_daily: number | null;
    rsi_weekly: number | null;
    macd_bull_cross: boolean;
    hit_52w_high: boolean;
    hit_52w_low: boolean;
    roc_positive: boolean;
    above_prev_month_high: boolean;
  };
}

async function fetchStockSentiment(ticker: string): Promise<StockSentimentDetail | null> {
  const res = await fetch(`${API}/api/sentiment/stock/${encodeURIComponent(ticker)}`);
  if (!res.ok) return null;
  return res.json();
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

/** Row background color based on zone */
function zoneRowStyle(zone: string): string {
  switch (zone) {
    case "Strong": return "bg-emerald-50 hover:bg-emerald-100";
    case "Bullish": return "bg-emerald-50/50 hover:bg-emerald-50";
    case "Neutral": return "bg-slate-50 hover:bg-slate-100";
    case "Weak": return "bg-amber-50/50 hover:bg-amber-50";
    case "Bear": return "bg-red-50/50 hover:bg-red-50";
    default: return "bg-slate-50 hover:bg-slate-100";
  }
}

function MetricPill({ label, value }: { label: string; value: boolean }) {
  return (
    <span className={cn(
      "inline-flex items-center gap-0.5 rounded px-1.5 py-0.5 text-[10px] font-medium",
      value ? "bg-emerald-50 text-emerald-700" : "bg-slate-50 text-slate-400"
    )}>
      {value ? <CheckCircle2 className="h-2.5 w-2.5" /> : <XCircle className="h-2.5 w-2.5" />}
      {label}
    </span>
  );
}

interface StockListDrawerProps {
  metric: SentimentMetric | null;
  open: boolean;
  onClose: () => void;
}

function StockDetailCard({ ticker }: { ticker: string }) {
  const { data, isLoading } = useSWR(
    `stock-sentiment-${ticker}`,
    () => fetchStockSentiment(ticker),
  );

  if (isLoading) return <Skeleton className="h-24 rounded-lg" />;
  if (!data || !data.metrics) {
    return <div className="text-xs text-slate-400 py-2 text-center">No sentiment data available</div>;
  }

  const m = data.metrics;
  return (
    <div className="bg-white rounded-lg border border-slate-100 p-3 space-y-2">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-sm font-semibold font-mono text-slate-800">{data.ticker}</span>
          {data.sector_index && <span className="text-[10px] text-slate-400 ml-2">{data.sector_index}</span>}
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-lg font-bold font-mono tabular-nums", zoneTextColor(data.zone))}>
            {data.composite_score.toFixed(1)}
          </span>
          <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-medium", zoneBadgeColor(data.zone))}>
            {data.zone}
          </span>
        </div>
      </div>

      <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
        <div
          className={cn("h-full rounded-full", data.composite_score >= 55 ? "bg-emerald-500" : data.composite_score >= 30 ? "bg-amber-400" : "bg-red-400")}
          style={{ width: `${Math.min(data.composite_score, 100)}%` }}
        />
      </div>

      <div className="flex flex-wrap gap-1">
        <MetricPill label="10 EMA" value={m.above_10ema} />
        <MetricPill label="21 EMA" value={m.above_21ema} />
        <MetricPill label="50 EMA" value={m.above_50ema} />
        <MetricPill label="200 EMA" value={m.above_200ema} />
        <MetricPill label="Golden Cross" value={m.golden_cross} />
        <MetricPill label="MACD Bull" value={m.macd_bull_cross} />
        <MetricPill label="52W High" value={m.hit_52w_high} />
        <MetricPill label="52W Low" value={m.hit_52w_low} />
        <MetricPill label="ROC+" value={m.roc_positive} />
        <MetricPill label="Prev Month High" value={m.above_prev_month_high} />
      </div>

      {(m.rsi_daily !== null || m.rsi_weekly !== null) && (
        <div className="flex gap-4 text-[10px] text-slate-500">
          {m.rsi_daily !== null && (
            <span>RSI (Daily): <span className="font-mono font-medium">{m.rsi_daily.toFixed(1)}</span></span>
          )}
          {m.rsi_weekly !== null && (
            <span>RSI (Weekly): <span className="font-mono font-medium">{m.rsi_weekly.toFixed(1)}</span></span>
          )}
        </div>
      )}

      <div className="text-[10px] text-slate-300">As of {data.date}</div>
    </div>
  );
}

export function StockListDrawer({ metric, open, onClose }: StockListDrawerProps) {
  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);

  if (!metric) return null;

  // Handle both enriched objects and plain strings (backward compat)
  const tickers: TickerWithScore[] = (metric.tickers ?? []).map((t) => {
    if (typeof t === "string") return { ticker: t, score: 0, zone: "Neutral" };
    return t;
  });

  const handleClose = () => {
    setSelectedTicker(null);
    onClose();
  };

  return (
    <Sheet open={open} onOpenChange={(v) => !v && handleClose()}>
      <SheetContent className="w-full sm:max-w-md overflow-y-auto">
        <SheetHeader className="pb-4 border-b border-slate-200">
          {selectedTicker ? (
            <>
              <button
                type="button"
                onClick={() => setSelectedTicker(null)}
                className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-700 transition-colors mb-1"
              >
                <ArrowLeft className="h-3 w-3" />
                Back to list
              </button>
              <SheetTitle className="text-base font-semibold text-foreground">
                {selectedTicker} — Sentiment Detail
              </SheetTitle>
              <SheetDescription className="text-sm text-muted-foreground">
                Per-stock technical sentiment scoring
              </SheetDescription>
            </>
          ) : (
            <>
              <SheetTitle className="text-base font-semibold text-foreground">
                {metric.label}
              </SheetTitle>
              <SheetDescription className="text-sm text-muted-foreground">
                {metric.count} of {metric.total} stocks ({metric.pct.toFixed(1)}%)
                — sorted by sentiment score, tap for detail
              </SheetDescription>
            </>
          )}
        </SheetHeader>

        {selectedTicker ? (
          <div className="mt-4 px-4">
            <StockDetailCard ticker={selectedTicker} />
          </div>
        ) : tickers.length > 0 ? (
          <div className="mt-4 px-4 space-y-1">
            {tickers.map((t, idx) => (
              <button
                key={t.ticker}
                type="button"
                onClick={() => setSelectedTicker(t.ticker)}
                className={cn(
                  "w-full flex items-center gap-2 rounded-lg px-3 py-2 text-left transition-colors cursor-pointer",
                  zoneRowStyle(t.zone)
                )}
                title={`${t.ticker}: ${t.score.toFixed(1)} (${t.zone})`}
              >
                <span className="text-[10px] font-mono text-slate-400 w-5 shrink-0">
                  {idx + 1}.
                </span>
                <span className="text-xs font-mono font-semibold flex-1">
                  {t.ticker}
                </span>
                <span className={cn("text-xs font-mono tabular-nums font-bold", zoneTextColor(t.zone))}>
                  {t.score.toFixed(1)}
                </span>
                <span className={cn(
                  "rounded-full px-1.5 py-0.5 text-[9px] font-medium shrink-0",
                  zoneBadgeColor(t.zone)
                )}>
                  {t.zone}
                </span>
              </button>
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
