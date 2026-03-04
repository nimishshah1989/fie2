"use client";

import { useState, useMemo, useCallback } from "react";
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

type AlertStatus = "PENDING" | "APPROVED" | "DENIED";
type SignalFilter = "all" | "BULLISH" | "BEARISH" | "NEUTRAL";
type SortBy = "newest" | "oldest" | "ticker";

export default function CommandCenter() {
  const { alerts, pending, approved, denied, bullish, bearish, isLoading } =
    useAlerts();

  const [statusFilters, setStatusFilters] = useState<Set<AlertStatus>>(new Set(["PENDING"]));
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [sortBy, setSortBy] = useState<SortBy>("newest");

  const toggleStatus = useCallback((status: AlertStatus) => {
    setStatusFilters((prev) => {
      const next = new Set(prev);
      if (next.has(status)) {
        next.delete(status);
      } else {
        next.add(status);
      }
      return next;
    });
  }, []);

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

    // Filter by status checkboxes — empty set means show nothing
    result = result.filter((a) => statusFilters.has(a.status as AlertStatus));

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
  }, [alerts, statusFilters, signalFilter, sortBy]);

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-xl sm:text-2xl font-bold tracking-tight">Command Center</h1>
        <p className="text-xs sm:text-sm text-muted-foreground">
          Real-time overview of all TradingView alerts
        </p>
      </div>

      {/* API Warning */}
      <ApiWarning />

      {/* Stats Row */}
      <StatsRow stats={stats} />

      {/* Status Filters */}
      <div className="flex flex-wrap items-center gap-4">
        <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Show:</span>
        {(["PENDING", "APPROVED", "DENIED"] as AlertStatus[]).map((status) => {
          const checked = statusFilters.has(status);
          const colorMap: Record<AlertStatus, string> = {
            PENDING: "accent-blue-600",
            APPROVED: "accent-emerald-600",
            DENIED: "accent-red-600",
          };
          return (
            <label key={status} className="flex items-center gap-1.5 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={checked}
                onChange={() => toggleStatus(status)}
                className={`h-3.5 w-3.5 rounded ${colorMap[status]}`}
              />
              <span className="text-sm text-foreground">{status.charAt(0) + status.slice(1).toLowerCase()}</span>
            </label>
          );
        })}
      </div>

      {/* Signal & Sort Filters */}
      <div className="flex flex-col sm:flex-row gap-2 sm:gap-3 sm:items-center">
        <Select
          value={signalFilter}
          onValueChange={(v) => setSignalFilter(v as SignalFilter)}
        >
          <SelectTrigger className="w-full sm:w-[180px]">
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
          <SelectTrigger className="w-full sm:w-[180px]">
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
            statusFilters.size < 3 || signalFilter !== "all"
              ? "No alerts match the current filters. Try adjusting the status or signal filters."
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
