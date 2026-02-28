"use client";

import { useState, useMemo } from "react";
import { useActionables } from "@/hooks/use-actionables";
import { ActionableCard } from "@/components/actionable-card";
import { StatsRow } from "@/components/stats-row";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPct } from "@/lib/utils";
import { AlertTriangle } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type TriggerFilter = "all" | "TP_HIT" | "SL_HIT";

export default function ActionablesPage() {
  const { actionables, error, isLoading } = useActionables();
  const [triggerFilter, setTriggerFilter] = useState<TriggerFilter>("all");

  const tpHits = useMemo(
    () => actionables.filter((a) => a.trigger_type === "TP_HIT").length,
    [actionables]
  );
  const slHits = useMemo(
    () => actionables.filter((a) => a.trigger_type === "SL_HIT").length,
    [actionables]
  );
  const avgPnl = useMemo(() => {
    if (actionables.length === 0) return 0;
    return (
      actionables.reduce((sum, a) => sum + a.pnl_pct, 0) / actionables.length
    );
  }, [actionables]);

  const filtered = useMemo(() => {
    if (triggerFilter === "all") return actionables;
    return actionables.filter((a) => a.trigger_type === triggerFilter);
  }, [actionables, triggerFilter]);

  const stats = [
    { label: "Total Triggered", value: actionables.length },
    { label: "Target Hit", value: tpHits, color: "text-emerald-600" },
    { label: "Stop Loss Hit", value: slHits, color: "text-red-600" },
    {
      label: "Avg P&L",
      value: formatPct(avgPnl),
      color: avgPnl >= 0 ? "text-emerald-600" : "text-red-600",
    },
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <AlertTriangle className="size-5 sm:size-6 text-amber-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Actionables</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Alerts where current price has hit stop loss or target price
        </p>
      </div>

      {/* Stats Row */}
      {!isLoading && <StatsRow stats={stats} />}

      {/* Filters */}
      <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
        <Select
          value={triggerFilter}
          onValueChange={(v) => setTriggerFilter(v as TriggerFilter)}
        >
          <SelectTrigger className="w-full sm:w-[180px]">
            <SelectValue placeholder="Trigger type" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Triggers</SelectItem>
            <SelectItem value="TP_HIT">Target Hit</SelectItem>
            <SelectItem value="SL_HIT">Stop Loss Hit</SelectItem>
          </SelectContent>
        </Select>

        <span className="text-xs text-muted-foreground ml-auto">
          {filtered.length} alert{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load actionables data. Please try again later.
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-52 rounded-xl" />
          ))}
        </div>
      )}

      {/* Empty State */}
      {!isLoading && !error && filtered.length === 0 && (
        <EmptyState
          icon={<AlertTriangle className="h-12 w-12" />}
          title="No actionable alerts"
          description={
            triggerFilter !== "all"
              ? "No alerts match the selected trigger filter."
              : "Alerts will appear here when current price hits their stop loss or target price."
          }
        />
      )}

      {/* Card Grid */}
      {!isLoading && !error && filtered.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filtered.map((alert) => (
            <ActionableCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}
    </div>
  );
}
