"use client";

import { useState, useMemo, useCallback } from "react";
import type { Alert } from "@/lib/types";
import { postAction } from "@/lib/api";
import { useAlerts } from "@/hooks/use-alerts";
import { StatsRow } from "@/components/stats-row";
import { ApiWarning } from "@/components/api-warning";
import { EmptyState } from "@/components/empty-state";
import { AlertCardCompact } from "@/components/alert-card-compact";
import { FmActionDialog } from "@/components/fm-action-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type SignalFilter = "ALL" | "BULLISH" | "BEARISH" | "NEUTRAL";
type SortBy = "newest" | "oldest" | "ticker";

export default function TradeCenterPage() {
  const { pending, bullish, bearish, alerts, error, isLoading, mutate } =
    useAlerts();

  const [signalFilter, setSignalFilter] = useState<SignalFilter>("ALL");
  const [sortBy, setSortBy] = useState<SortBy>("newest");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [isWatchMode, setIsWatchMode] = useState(false);

  // Filter + sort pending alerts
  const filteredAlerts = useMemo(() => {
    let filtered = [...pending];

    // Signal filter
    if (signalFilter !== "ALL") {
      filtered = filtered.filter((a) => a.signal_direction === signalFilter);
    }

    // Sort
    switch (sortBy) {
      case "newest":
        filtered.sort((a, b) => {
          const ta = a.received_at ?? "";
          const tb = b.received_at ?? "";
          return tb.localeCompare(ta);
        });
        break;
      case "oldest":
        filtered.sort((a, b) => {
          const ta = a.received_at ?? "";
          const tb = b.received_at ?? "";
          return ta.localeCompare(tb);
        });
        break;
      case "ticker":
        filtered.sort((a, b) => a.ticker.localeCompare(b.ticker));
        break;
    }

    return filtered;
  }, [pending, signalFilter, sortBy]);

  // Approve handler — open FM Dialog
  const handleApprove = useCallback(
    (id: number) => {
      const alert = pending.find((a) => a.id === id);
      if (alert) {
        setSelectedAlert(alert);
        setIsWatchMode(false);
        setDialogOpen(true);
      }
    },
    [pending]
  );

  // Watch handler — open FM Dialog in watch mode
  const handleWatch = useCallback(
    (id: number) => {
      const alert = pending.find((a) => a.id === id);
      if (alert) {
        setSelectedAlert(alert);
        setIsWatchMode(true);
        setDialogOpen(true);
      }
    },
    [pending]
  );

  // Deny handler — directly call API
  const handleDeny = useCallback(
    async (id: number) => {
      try {
        await postAction({ alert_id: id, decision: "DENIED" });
        mutate();
      } catch {
        // silently fail — user can retry
      }
    },
    [mutate]
  );

  // FM Dialog submitted
  const handleDialogSubmitted = useCallback(() => {
    setDialogOpen(false);
    setSelectedAlert(null);
    setIsWatchMode(false);
    mutate();
  }, [mutate]);

  // Stats
  const stats = [
    {
      label: "Pending",
      value: pending.length,
      color: "text-amber-600",
    },
    {
      label: "Bullish",
      value: bullish,
      color: "text-emerald-600",
    },
    {
      label: "Bearish",
      value: bearish,
      color: "text-red-600",
    },
    {
      label: "Total Alerts",
      value: alerts.length,
      color: "text-blue-600",
    },
  ];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-foreground">Trade Center</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Pending alerts awaiting FM decision
        </p>
      </div>

      {/* API Warning */}
      <ApiWarning />

      {/* Stats Row */}
      <StatsRow stats={stats} />

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <Select
          value={signalFilter}
          onValueChange={(v) => setSignalFilter(v as SignalFilter)}
        >
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Signal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="ALL">All Signals</SelectItem>
            <SelectItem value="BULLISH">Bullish</SelectItem>
            <SelectItem value="BEARISH">Bearish</SelectItem>
            <SelectItem value="NEUTRAL">Neutral</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={sortBy}
          onValueChange={(v) => setSortBy(v as SortBy)}
        >
          <SelectTrigger className="w-[150px]">
            <SelectValue placeholder="Sort by" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="newest">Newest</SelectItem>
            <SelectItem value="oldest">Oldest</SelectItem>
            <SelectItem value="ticker">Ticker</SelectItem>
          </SelectContent>
        </Select>

        <span className="text-xs text-muted-foreground ml-auto">
          {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="rounded-xl border p-4 space-y-3">
              <div className="flex items-center justify-between">
                <Skeleton className="h-5 w-24" />
                <Skeleton className="h-5 w-12" />
              </div>
              <Skeleton className="h-4 w-48" />
              <Skeleton className="h-10 w-full" />
              <div className="flex gap-2">
                <Skeleton className="h-8 flex-1" />
                <Skeleton className="h-8 flex-1" />
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error State */}
      {error && !isLoading && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          Failed to load alerts. Please check your API connection.
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && filteredAlerts.length === 0 && (
        <EmptyState
          title="No pending alerts"
          description={
            signalFilter !== "ALL"
              ? "No pending alerts match the selected signal filter. Try selecting 'All Signals'."
              : "All alerts have been reviewed. New alerts will appear here automatically."
          }
        />
      )}

      {/* Card Grid */}
      {!isLoading && filteredAlerts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAlerts.map((alert) => (
            <AlertCardCompact
              key={alert.id}
              alert={alert}
              onApprove={handleApprove}
              onDeny={handleDeny}
              onWatch={handleWatch}
            />
          ))}
        </div>
      )}

      {/* FM Action Dialog */}
      <FmActionDialog
        alert={selectedAlert}
        open={dialogOpen}
        onOpenChange={setDialogOpen}
        onSubmitted={handleDialogSubmitted}
        watchMode={isWatchMode}
      />
    </div>
  );
}
