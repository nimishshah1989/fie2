"use client";

import { useState, useMemo } from "react";
import { CheckCircle2, Search } from "lucide-react";
import { useActioned } from "@/hooks/use-actioned";
import type { ActionedAlert } from "@/lib/types";
import { cn, formatPct } from "@/lib/utils";
import { ActionedCard } from "@/components/actioned-card";
import { ActionedDetailSheet } from "@/components/actioned-detail-sheet";
import { StatsRow } from "@/components/stats-row";
import { EmptyState } from "@/components/empty-state";
import { PageInfo } from "@/components/page-info";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type TabKey = "active" | "triggered" | "closed";
type SignalFilter = "all" | "BULLISH" | "BEARISH";

export default function ActionedPage() {
  const { active, triggered, closed, error, isLoading } = useActioned();

  const [tab, setTab] = useState<TabKey>("active");
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<ActionedAlert | null>(null);

  // Pick the set for current tab
  const tabAlerts: ActionedAlert[] = tab === "active" ? active : tab === "triggered" ? triggered : closed;

  // Filter + search
  const filteredAlerts = useMemo(() => {
    let result = tabAlerts;
    if (signalFilter !== "all") {
      result = result.filter((a) => a.signal_direction === signalFilter);
    }
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((a) => a.ticker.toLowerCase().includes(q));
    }
    return result;
  }, [tabAlerts, signalFilter, search]);

  // Stats per tab
  const activeStats = useMemo(() => {
    const bullish = active.filter((a) => a.signal_direction === "BULLISH").length;
    const bearish = active.filter((a) => a.signal_direction === "BEARISH").length;
    const avgPnl = active.length > 0
      ? active.reduce((sum, a) => sum + (a.return_pct ?? 0), 0) / active.length
      : 0;
    return [
      { label: "Total Active", value: active.length },
      { label: "Bullish", value: bullish, color: "text-emerald-600" },
      { label: "Bearish", value: bearish, color: "text-red-600" },
      { label: "Avg Unrealized P&L", value: formatPct(avgPnl), color: avgPnl >= 0 ? "text-emerald-600" : "text-red-600" },
    ];
  }, [active]);

  const triggeredStats = useMemo(() => {
    const targetHits = triggered.filter((a) => a.target_hit).length;
    const slHits = triggered.filter((a) => a.sl_hit).length;
    return [
      { label: "Total Triggered", value: triggered.length },
      { label: "Target Hits", value: targetHits, color: "text-emerald-600" },
      { label: "SL Hits", value: slHits, color: "text-red-600" },
    ];
  }, [triggered]);

  const closedStats = useMemo(() => {
    const wins = closed.filter((a) => (a.closed_pnl_pct ?? 0) > 0).length;
    const winRate = closed.length > 0 ? (wins / closed.length) * 100 : 0;
    const avgPnl = closed.length > 0
      ? closed.reduce((sum, a) => sum + (a.closed_pnl_pct ?? 0), 0) / closed.length
      : 0;
    return [
      { label: "Total Closed", value: closed.length },
      { label: "Win Rate", value: `${winRate.toFixed(1)}%`, color: winRate >= 50 ? "text-emerald-600" : "text-red-600" },
      { label: "Avg Realized P&L", value: formatPct(avgPnl), color: avgPnl >= 0 ? "text-emerald-600" : "text-red-600" },
    ];
  }, [closed]);

  const currentStats = tab === "active" ? activeStats : tab === "triggered" ? triggeredStats : closedStats;

  const tabs: { key: TabKey; label: string; count: number }[] = [
    { key: "active", label: "Active", count: active.length },
    { key: "triggered", label: "Triggered", count: triggered.length },
    { key: "closed", label: "Closed", count: closed.length },
  ];

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <CheckCircle2 className="size-5 sm:size-6 text-teal-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-slate-800">Actioned Cards</h1>
        </div>
        <p className="text-xs sm:text-sm text-slate-500 mt-1">
          All FM-actioned alerts with live performance tracking
        </p>
      </div>

      <PageInfo>
        All FM-actioned alerts with live performance tracking. Active positions show unrealized P&L,
        triggered alerts highlight stop loss or target hits, and closed trades show locked-in returns.
      </PageInfo>

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-slate-200">
        {tabs.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
              tab === t.key
                ? "border-teal-600 text-teal-600"
                : "border-transparent text-slate-400 hover:text-slate-600 hover:border-slate-300"
            )}
          >
            {t.label}
            {t.count > 0 && (
              <span className="ml-1.5 text-xs text-slate-400">({t.count})</span>
            )}
          </button>
        ))}
      </div>

      {/* Stats Row */}
      {!isLoading && <StatsRow stats={currentStats} />}

      {/* Filter Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-3">
        <Select value={signalFilter} onValueChange={(v) => setSignalFilter(v as SignalFilter)}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="Signal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Signals</SelectItem>
            <SelectItem value="BULLISH">Bullish</SelectItem>
            <SelectItem value="BEARISH">Bearish</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative w-full sm:flex-1 sm:min-w-[200px] sm:max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-slate-400" />
          <Input
            placeholder="Search by ticker..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>

        <span className="text-xs text-slate-400 sm:ml-auto">
          {filteredAlerts.length} alert{filteredAlerts.length !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Error */}
      {error && !isLoading && (
        <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          Failed to load actioned alerts. Please check your API connection.
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
      {!isLoading && !error && filteredAlerts.length === 0 && (
        <EmptyState
          icon={<CheckCircle2 className="h-12 w-12" />}
          title={`No ${tab} alerts`}
          description={
            search || signalFilter !== "all"
              ? "Try adjusting your filters or search term."
              : tab === "active"
              ? "Active positions will appear here when the FM approves alerts."
              : tab === "triggered"
              ? "Triggered alerts appear when price hits stop loss or target."
              : "Closed trades appear when positions are manually closed."
          }
        />
      )}

      {/* Card Grid */}
      {!isLoading && !error && filteredAlerts.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAlerts.map((alert) => (
            <ActionedCard
              key={alert.id}
              alert={alert}
              onClick={() => setSelectedAlert(alert)}
            />
          ))}
        </div>
      )}

      {/* Detail Sheet */}
      <ActionedDetailSheet
        alert={selectedAlert}
        onClose={() => setSelectedAlert(null)}
      />
    </div>
  );
}
