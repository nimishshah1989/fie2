"use client";

import { useState, useMemo } from "react";
import { useActionables } from "@/hooks/use-actionables";
import { useClosedTrades } from "@/hooks/use-closed-trades";
import { ActionableCard } from "@/components/actionable-card";
import { StatsRow } from "@/components/stats-row";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { formatPct, formatPrice, cn } from "@/lib/utils";
import { AlertTriangle, CheckCircle2, TrendingUp, TrendingDown } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ClosedTrade } from "@/lib/types";

type TriggerFilter = "all" | "TP_HIT" | "SL_HIT";
type PageTab = "active" | "closed";

function ClosedTradeCard({ trade }: { trade: ClosedTrade }) {
  const isProfit = (trade.closed_pnl_pct ?? 0) >= 0;
  const actionCall = trade.action?.action_call ?? "";
  return (
    <div className="rounded-xl border bg-white p-4 space-y-3 shadow-sm border-l-4 border-l-slate-300">
      <div className="flex items-center justify-between">
        <span className="text-sm font-bold">{trade.ticker}</span>
        <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-600">
          {actionCall || "—"}
        </Badge>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div>
          <span className="text-xs text-muted-foreground">Entry</span>
          <div className="font-medium font-mono">{trade.entry_price ? formatPrice(trade.entry_price) : "—"}</div>
        </div>
        <div>
          <span className="text-xs text-muted-foreground">Closed At</span>
          <div className="font-medium font-mono">{formatPrice(trade.closed_price)}</div>
        </div>
      </div>
      <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
        <div className="flex items-center gap-1.5">
          {isProfit ? (
            <TrendingUp className="size-4 text-emerald-600" />
          ) : (
            <TrendingDown className="size-4 text-red-600" />
          )}
          <span className="text-xs text-muted-foreground">Realized P&L</span>
        </div>
        <span className={cn("text-sm font-bold", isProfit ? "text-emerald-600" : "text-red-600")}>
          {formatPct(trade.closed_pnl_pct)}
        </span>
      </div>
      <p className="text-[10px] text-slate-400">
        Closed {new Date(trade.closed_at).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
        {trade.days_since != null ? ` · ${trade.days_since}d after alert` : ""}
      </p>
    </div>
  );
}

export default function ActionablesPage() {
  const { actionables, error, isLoading, mutate } = useActionables();
  const { trades: closedTrades, isLoading: closedLoading } = useClosedTrades();
  const [triggerFilter, setTriggerFilter] = useState<TriggerFilter>("all");
  const [activeTab, setActiveTab] = useState<PageTab>("active");

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
    return actionables.reduce((sum, a) => sum + a.pnl_pct, 0) / actionables.length;
  }, [actionables]);

  const realizedPnl = useMemo(() => {
    if (closedTrades.length === 0) return 0;
    return closedTrades.reduce((sum, t) => sum + (t.closed_pnl_pct ?? 0), 0) / closedTrades.length;
  }, [closedTrades]);

  const filtered = useMemo(() => {
    if (triggerFilter === "all") return actionables;
    return actionables.filter((a) => a.trigger_type === triggerFilter);
  }, [actionables, triggerFilter]);

  const activeStats = [
    { label: "Total Triggered", value: actionables.length },
    { label: "Target Hit", value: tpHits, color: "text-emerald-600" },
    { label: "Stop Loss Hit", value: slHits, color: "text-red-600" },
    { label: "Avg P&L", value: formatPct(avgPnl), color: avgPnl >= 0 ? "text-emerald-600" : "text-red-600" },
  ];

  const closedStats = [
    { label: "Closed Trades", value: closedTrades.length },
    { label: "Avg Realized P&L", value: formatPct(realizedPnl), color: realizedPnl >= 0 ? "text-emerald-600" : "text-red-600" },
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

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-border">
        <button
          type="button"
          onClick={() => setActiveTab("active")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "active"
              ? "border-teal-600 text-teal-600"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          )}
        >
          Active
          {actionables.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({actionables.length})</span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setActiveTab("closed")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "closed"
              ? "border-teal-600 text-teal-600"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          )}
        >
          <span className="flex items-center gap-1">
            <CheckCircle2 className="h-3.5 w-3.5" />
            Closed Trades
          </span>
          {closedTrades.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({closedTrades.length})</span>
          )}
        </button>
      </div>

      {/* Active Tab */}
      {activeTab === "active" && (
        <>
          {!isLoading && <StatsRow stats={activeStats} />}

          <div className="flex items-center gap-2 sm:gap-3 flex-wrap">
            <Select value={triggerFilter} onValueChange={(v) => setTriggerFilter(v as TriggerFilter)}>
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

          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              Failed to load actionables data. Please try again later.
            </div>
          )}

          {isLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 6 }).map((_, i) => (
                <Skeleton key={i} className="h-52 rounded-xl" />
              ))}
            </div>
          )}

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

          {!isLoading && !error && filtered.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {filtered.map((alert) => (
                <ActionableCard key={alert.id} alert={alert} onClose={mutate} />
              ))}
            </div>
          )}
        </>
      )}

      {/* Closed Trades Tab */}
      {activeTab === "closed" && (
        <>
          {!closedLoading && <StatsRow stats={closedStats} />}

          {closedLoading && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-40 rounded-xl" />
              ))}
            </div>
          )}

          {!closedLoading && closedTrades.length === 0 && (
            <EmptyState
              icon={<CheckCircle2 className="h-12 w-12" />}
              title="No closed trades"
              description="Use the 'Close Trade' button on active actionable cards to record a closed position with locked-in P&L."
            />
          )}

          {!closedLoading && closedTrades.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
              {closedTrades.map((trade) => (
                <ClosedTradeCard key={trade.id} trade={trade} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
