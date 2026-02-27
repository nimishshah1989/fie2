"use client";

import { useState, useMemo } from "react";
import { useAlerts } from "@/hooks/use-alerts";
import { StatsRow } from "@/components/stats-row";
import { AlertCard } from "@/components/alert-card";
import { EmptyState } from "@/components/empty-state";
import { ApiWarning } from "@/components/api-warning";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SearchX } from "lucide-react";
import type { Alert } from "@/lib/types";

type SignalFilter = "all" | "BULLISH" | "BEARISH" | "NEUTRAL";
type SortBy = "newest" | "oldest" | "ticker";

export default function CommandCenter() {
  const { alerts, pending, approved, denied, bullish, bearish, isLoading } =
    useAlerts();

  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [sortBy, setSortBy] = useState<SortBy>("newest");

  const stats = [
    { label: "Total Alerts", value: alerts.length },
    { label: "Pending", value: pending.length, color: "text-blue-600" },
    { label: "Approved", value: approved.length, color: "text-emerald-600" },
    { label: "Denied", value: denied.length, color: "text-red-600" },
    { label: "Bullish", value: bullish, color: "text-emerald-600" },
    { label: "Bearish", value: bearish, color: "text-red-600" },
  ];

  const filteredAndSorted = useMemo(() => {
    let result: Alert[] = [...alerts];

    // Filter by signal direction
    if (signalFilter !== "all") {
      result = result.filter((a) => a.signal_direction === signalFilter);
    }

    // Sort
    switch (sortBy) {
      case "newest":
        result.sort(
          (a, b) =>
            new Date(b.received_at ?? 0).getTime() -
            new Date(a.received_at ?? 0).getTime()
        );
        break;
      case "oldest":
        result.sort(
          (a, b) =>
            new Date(a.received_at ?? 0).getTime() -
            new Date(b.received_at ?? 0).getTime()
        );
        break;
      case "ticker":
        result.sort((a, b) => a.ticker.localeCompare(b.ticker));
        break;
    }

    return result;
  }, [alerts, signalFilter, sortBy]);

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="text-muted-foreground">
          Real-time overview of all TradingView alerts
        </p>
      </div>

      {/* API Warning */}
      <ApiWarning />

      {/* Stats Row */}
      <StatsRow stats={stats} />

      {/* Filters Row */}
      <div className="flex gap-3 items-center">
        <Select
          value={signalFilter}
          onValueChange={(v) => setSignalFilter(v as SignalFilter)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="All Signals" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Signals</SelectItem>
            <SelectItem value="BULLISH">Bullish</SelectItem>
            <SelectItem value="BEARISH">Bearish</SelectItem>
            <SelectItem value="NEUTRAL">Neutral</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={sortBy}
          onValueChange={(v) => setSortBy(v as SortBy)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Newest First" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest First</SelectItem>
            <SelectItem value="oldest">Oldest First</SelectItem>
            <SelectItem value="ticker">Ticker A-Z</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Card Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-[200px] rounded-xl" />
          ))}
        </div>
      ) : filteredAndSorted.length === 0 ? (
        <EmptyState
          icon={<SearchX className="h-12 w-12" />}
          title="No alerts found"
          description={
            signalFilter !== "all"
              ? `No ${signalFilter.toLowerCase()} alerts to display. Try changing the filter.`
              : "No alerts have been received yet. They will appear here automatically."
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAndSorted.map((alert) => (
            <AlertCard key={alert.id} alert={alert} showActions={false} />
          ))}
        </div>
      )}
    </div>
  );
}
