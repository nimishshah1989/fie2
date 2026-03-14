"use client";

import { useSentiment } from "@/hooks/use-sentiment";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import { BarChart2, RefreshCw, TrendingUp, TrendingDown, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

const API = process.env.NEXT_PUBLIC_API_URL || "";

interface SentimentMetric {
  key: string;
  label: string;
  count: number;
  total: number;
  pct: number;
  invert?: boolean;
}

interface SentimentSection {
  label: string;
  metrics: SentimentMetric[];
  period_note?: string;
}

function MetricCard({ metric }: { metric: SentimentMetric }) {
  const { count, total, pct, invert } = metric;
  const effectivePct = invert ? 100 - pct : pct;

  const color =
    effectivePct >= 60
      ? "text-emerald-600"
      : effectivePct >= 40
      ? "text-amber-600"
      : "text-red-600";

  const barColor =
    effectivePct >= 60
      ? "bg-emerald-500"
      : effectivePct >= 40
      ? "bg-amber-500"
      : "bg-red-500";

  const Icon =
    effectivePct >= 55 ? TrendingUp : effectivePct >= 45 ? Minus : TrendingDown;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
      <div className="flex items-start justify-between">
        <p className="text-sm text-slate-500 leading-tight max-w-[75%]">{metric.label}</p>
        <Icon className={cn("h-4 w-4 flex-shrink-0 mt-0.5", color)} />
      </div>

      <div className="flex items-end gap-2">
        <span className={cn("text-3xl font-bold font-mono tabular-nums", color)}>
          {count}
        </span>
        <span className="text-sm text-slate-400 mb-1">/ {total}</span>
      </div>

      {/* Progress bar */}
      <div className="space-y-1">
        <div className="w-full bg-slate-100 rounded-full h-2">
          <div
            className={cn("h-2 rounded-full transition-all", barColor)}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
        <p className={cn("text-sm font-semibold font-mono tabular-nums text-right", color)}>
          {pct.toFixed(1)}%
        </p>
      </div>
    </div>
  );
}

function SectionHeader({ label, note }: { label: string; note?: string }) {
  return (
    <div className="mt-6 mb-3">
      <h2 className="text-base font-semibold text-slate-700">{label}</h2>
      {note && <p className="text-xs text-slate-400 mt-0.5">{note}</p>}
    </div>
  );
}

export default function SentimentPage() {
  const { data, error, isLoading, mutate } = useSentiment();

  async function handleRefresh() {
    await fetch(`${API}/api/sentiment/refresh`, { method: "POST" });
    mutate();
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2">
            <BarChart2 className="size-5 sm:size-6 text-teal-600" />
            <h1 className="text-xl sm:text-2xl font-bold text-foreground">Sentiment Indicators</h1>
          </div>
          <p className="text-xs sm:text-sm text-muted-foreground mt-1">
            Market breadth across Nifty 500 — EMA, RSI, 52-week levels, and advance/decline
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={handleRefresh}
          className="text-xs gap-1.5"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Refresh
        </Button>
      </div>

      {/* Universe badge */}
      {data && (
        <div className="flex items-center gap-3 flex-wrap">
          <div className="text-sm text-slate-600">
            <span className="font-semibold">{data.universe}</span>
            <span className="text-slate-400 mx-2">·</span>
            <span>{data.stocks_computed} stocks computed</span>
          </div>
          {data.computed_at && (
            <span className="text-xs text-slate-400">
              Last updated{" "}
              {new Date(data.computed_at).toLocaleString("en-IN", {
                timeZone: "Asia/Kolkata",
                day: "numeric",
                month: "short",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              IST
            </span>
          )}
          {data.cached && (
            <span className="text-[10px] bg-slate-100 text-slate-500 rounded-full px-2 py-0.5">
              Cached
            </span>
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
        <div className="space-y-6">
          {[4, 4, 3].map((count, si) => (
            <div key={si}>
              <Skeleton className="h-5 w-48 mb-3 rounded" />
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {Array.from({ length: count }).map((_, i) => (
                  <Skeleton key={i} className="h-36 rounded-xl" />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Empty / No data */}
      {!isLoading && !error && !data && (
        <div className="flex flex-col items-center justify-center py-20 text-center">
          <BarChart2 className="h-12 w-12 text-muted-foreground/40 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No sentiment data yet</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
            Sentiment indicators are computed after market close. Click Refresh to trigger computation.
          </p>
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && data && (
        <>
          {/* Short Term Trend */}
          {data.short_term_trend?.metrics?.length > 0 && (
            <>
              <SectionHeader label={data.short_term_trend.label} />
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {data.short_term_trend.metrics.map((m: SentimentMetric) => (
                  <MetricCard key={m.key} metric={m} />
                ))}
              </div>
            </>
          )}

          {/* Broad Trend */}
          {data.broad_trend?.metrics?.length > 0 && (
            <>
              <SectionHeader label={data.broad_trend.label} />
              <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
                {data.broad_trend.metrics.map((m: SentimentMetric) => (
                  <MetricCard key={m.key} metric={m} />
                ))}
              </div>
            </>
          )}

          {/* Advance / Decline */}
          {data.advance_decline?.metrics?.length > 0 && (
            <>
              <SectionHeader
                label={data.advance_decline.label}
                note={data.advance_decline.period_note}
              />
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                {data.advance_decline.metrics.map((m: SentimentMetric) => (
                  <MetricCard key={m.key} metric={m} />
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
