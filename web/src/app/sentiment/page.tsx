"use client";

import { useState } from "react";
import { useSentiment } from "@/hooks/use-sentiment";
import { useSentimentHistory } from "@/hooks/use-sentiment-history";
import { CompositeGauge } from "@/components/sentiment/CompositeGauge";
import { IndicatorRow } from "@/components/sentiment/IndicatorRow";
import { StockListDrawer } from "@/components/sentiment/StockListDrawer";
import { SentimentHistoryChart } from "@/components/sentiment/SentimentHistoryChart";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { BarChart2, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SentimentMetric } from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

type LayerKey = "short_term_trend" | "broad_trend" | "advance_decline" | "momentum" | "extremes";

const LAYER_TABS: { key: LayerKey; label: string }[] = [
  { key: "short_term_trend", label: "Short-Term" },
  { key: "broad_trend", label: "Broad Trend" },
  { key: "advance_decline", label: "Advance/Decline" },
  { key: "momentum", label: "Momentum" },
  { key: "extremes", label: "Extremes" },
];

const LAYER_SCORE_KEYS: { key: string; label: string }[] = [
  { key: "short_term", label: "Short-Term" },
  { key: "broad_trend", label: "Broad Trend" },
  { key: "adv_decline", label: "A/D" },
  { key: "momentum", label: "Momentum" },
  { key: "extremes", label: "Extremes" },
];

function scoreColor(score: number): string {
  if (score >= 60) return "text-emerald-600";
  if (score >= 40) return "text-amber-600";
  return "text-red-600";
}

export default function SentimentPage() {
  const { data, error, isLoading, mutate } = useSentiment();
  const { data: historyData } = useSentimentHistory();
  const [activeLayer, setActiveLayer] = useState<LayerKey>("short_term_trend");
  const [selectedMetric, setSelectedMetric] = useState<SentimentMetric | null>(null);

  async function handleRefresh() {
    try {
      const res = await fetch(`${API}/api/sentiment/refresh`, { method: "POST" });
      if (!res.ok) console.error("Sentiment refresh failed:", res.status);
    } catch (err) {
      console.error("Sentiment refresh failed:", err);
    }
    mutate();
  }

  const layerMetrics = data?.[activeLayer]?.metrics ?? [];
  const layerScores = data?.layer_scores ?? {};
  const history = historyData?.history ?? [];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BarChart2 className="size-5 sm:size-6 text-teal-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">Sentiment Dashboard</h1>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Market breadth across Nifty 500 — 26 indicators, 5 layers, composite score
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={handleRefresh} className="text-xs gap-1.5">
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Universe badge */}
      {data && (
        <div className="flex items-center gap-3 flex-wrap">
          <div className="text-sm text-slate-600">
            <span className="font-semibold">{data.universe}</span>
            <span className="text-slate-400 mx-2">&middot;</span>
            <span>{data.stocks_computed} stocks computed</span>
          </div>
          {data.computed_at && (
            <span className="text-xs text-slate-400">
              Last updated{" "}
              {new Date(data.computed_at).toLocaleString("en-IN", {
                timeZone: "Asia/Kolkata",
                day: "numeric", month: "short", year: "numeric",
                hour: "2-digit", minute: "2-digit",
              })}{" "}IST
            </span>
          )}
          {data.cached && (
            <span className="text-[10px] bg-slate-100 text-slate-500 rounded-full px-2 py-0.5">Cached</span>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load sentiment data. The backend may still be computing — try refreshing.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-40 rounded-xl" />
          <div className="grid grid-cols-5 gap-3">
            {Array.from({ length: 5 }).map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)}
          </div>
          <Skeleton className="h-[120px] rounded-xl" />
        </div>
      )}

      {/* Main content */}
      {!isLoading && !error && data && (
        <>
          {/* Gauge + Layer Scores */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            {/* Composite Gauge */}
            <div className="bg-white rounded-xl border border-slate-200 p-5 flex items-center justify-center">
              <CompositeGauge
                score={data.composite_score ?? 0}
                zone={data.zone ?? "Neutral"}
              />
            </div>

            {/* Layer Score Cards */}
            <div className="lg:col-span-2 grid grid-cols-2 sm:grid-cols-5 gap-3">
              {LAYER_SCORE_KEYS.map(({ key, label }) => {
                const val = layerScores[key] ?? 0;
                return (
                  <div key={key} className="bg-white rounded-xl border border-slate-200 p-4 text-center">
                    <p className="text-xs text-slate-400 mb-1">{label}</p>
                    <p className={cn("text-2xl font-bold font-mono tabular-nums", scoreColor(val))}>
                      {val.toFixed(0)}
                    </p>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Signal Pills */}
          {data.zone && (
            <div className="flex gap-2 flex-wrap">
              {data.zone === "Strong" || data.zone === "Bullish" ? (
                <span className="bg-emerald-50 text-emerald-700 border border-emerald-200 rounded-full px-3 py-1 text-xs font-medium">
                  {data.zone} Market
                </span>
              ) : data.zone === "Weak" || data.zone === "Bear" ? (
                <span className="bg-red-50 text-red-700 border border-red-200 rounded-full px-3 py-1 text-xs font-medium">
                  {data.zone} Market
                </span>
              ) : (
                <span className="bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-3 py-1 text-xs font-medium">
                  Neutral Market
                </span>
              )}
            </div>
          )}

          {/* History Chart */}
          <div className="bg-white rounded-xl border border-slate-200 p-4">
            <p className="text-xs text-slate-400 mb-2">20-Week Composite Score</p>
            <SentimentHistoryChart history={history} />
          </div>

          {/* Layer Tabs */}
          <div className="flex items-center gap-1 border-b border-border overflow-x-auto">
            {LAYER_TABS.map(({ key, label }) => (
              <button
                key={key}
                type="button"
                onClick={() => setActiveLayer(key)}
                className={cn(
                  "px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
                  activeLayer === key
                    ? "border-teal-600 text-teal-600"
                    : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
                )}
              >
                {label}
                {data[key]?.metrics?.length > 0 && (
                  <span className="ml-1.5 text-xs text-muted-foreground">
                    ({data[key].metrics.length})
                  </span>
                )}
              </button>
            ))}
          </div>

          {/* Indicator Rows */}
          <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100">
            {layerMetrics.length > 0 ? (
              layerMetrics.map((m: SentimentMetric) => (
                <IndicatorRow
                  key={m.key}
                  metric={m}
                  onClick={setSelectedMetric}
                />
              ))
            ) : (
              <div className="py-8 text-center text-sm text-slate-400">
                No indicators available for this layer yet.
              </div>
            )}
          </div>
        </>
      )}

      {/* Empty state */}
      {!isLoading && !error && !data && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BarChart2 className="h-12 w-12 text-muted-foreground/40 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No sentiment data yet</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
            Sentiment indicators are computed after market close. Click Refresh to trigger computation.
          </p>
        </div>
      )}

      {/* Stock List Drawer */}
      <StockListDrawer
        metric={selectedMetric}
        open={!!selectedMetric}
        onClose={() => setSelectedMetric(null)}
      />
    </div>
  );
}
