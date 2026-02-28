"use client";

import { usePerformance } from "@/hooks/use-performance";
import { PerformanceCard } from "@/components/performance-card";
import { StatsRow } from "@/components/stats-row";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPct } from "@/lib/utils";
import { BarChart3 } from "lucide-react";

export default function PerformancePage() {
  const { performance, error, isLoading } = usePerformance();

  const totalTrades = performance.length;
  const profitable = performance.filter((a) => (a.return_pct ?? 0) > 0).length;
  const lossmaking = performance.filter((a) => (a.return_pct ?? 0) < 0).length;
  const avgReturn =
    totalTrades > 0
      ? performance.reduce((sum, a) => sum + (a.return_pct ?? 0), 0) / totalTrades
      : 0;
  const ratioTrades = performance.filter((a) => a.is_ratio_trade).length;

  const stats = [
    { label: "Total Trades", value: totalTrades },
    { label: "Profitable", value: profitable, color: "text-emerald-600" },
    { label: "Loss-making", value: lossmaking, color: "text-red-600" },
    {
      label: "Avg Return",
      value: formatPct(avgReturn),
      color: avgReturn >= 0 ? "text-emerald-600" : "text-red-600",
    },
    { label: "Ratio Trades", value: ratioTrades },
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <BarChart3 className="size-5 sm:size-6 text-blue-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Alert Performance</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Track returns on FM-approved alerts
        </p>
      </div>

      {/* Stats Row */}
      {!isLoading && <StatsRow stats={stats} />}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load performance data. Please try again later.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-44 rounded-xl" />
          ))}
        </div>
      )}

      {/* Card Grid */}
      {!isLoading && !error && performance.length === 0 && (
        <EmptyState
          title="No performance data yet"
          description="Approved alerts with tracked returns will appear here."
        />
      )}

      {!isLoading && !error && performance.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {performance.map((alert) => (
            <PerformanceCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
