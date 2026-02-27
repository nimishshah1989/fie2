"use client";

import { useState, useMemo } from "react";
import { CheckCircle2, Search } from "lucide-react";
import { useAlerts } from "@/hooks/use-alerts";
import type { Alert } from "@/lib/types";
import { StatsRow } from "@/components/stats-row";
import { ApprovedCard } from "@/components/approved-card";
import { DetailPanel } from "@/components/detail-panel";
import { EmptyState } from "@/components/empty-state";
import { Skeleton } from "@/components/ui/skeleton";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

type UrgencyFilter = "all" | "IMMEDIATELY" | "WITHIN_A_WEEK" | "WITHIN_A_MONTH";
type SignalFilter = "all" | "BULLISH" | "BEARISH";

export default function ApprovedPage() {
  const { approved, isLoading } = useAlerts();

  const [urgencyFilter, setUrgencyFilter] = useState<UrgencyFilter>("all");
  const [signalFilter, setSignalFilter] = useState<SignalFilter>("all");
  const [search, setSearch] = useState("");
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);

  // Count urgency categories
  const immediatelyCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "IMMEDIATELY").length,
    [approved]
  );
  const withinWeekCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "WITHIN_A_WEEK").length,
    [approved]
  );
  const withinMonthCount = useMemo(
    () => approved.filter((a) => a.action?.priority === "WITHIN_A_MONTH").length,
    [approved]
  );

  // Filter approved alerts
  const filteredAlerts = useMemo(() => {
    let result = approved;

    if (urgencyFilter !== "all") {
      result = result.filter((a) => a.action?.priority === urgencyFilter);
    }

    if (signalFilter !== "all") {
      result = result.filter((a) => a.signal_direction === signalFilter);
    }

    if (search.trim()) {
      const q = search.trim().toLowerCase();
      result = result.filter((a) => a.ticker.toLowerCase().includes(q));
    }

    return result;
  }, [approved, urgencyFilter, signalFilter, search]);

  function handleCardClick(alert: Alert) {
    if (selectedAlert?.id === alert.id) {
      setSelectedAlert(null);
    } else {
      setSelectedAlert(alert);
    }
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Approved Cards</h1>
        <p className="text-sm text-muted-foreground mt-1">
          FM-approved alerts with action recommendations
        </p>
      </div>

      {/* Stats Row */}
      <StatsRow
        stats={[
          {
            label: "Total Approved",
            value: isLoading ? "-" : approved.length,
          },
          {
            label: "Immediately",
            value: isLoading ? "-" : immediatelyCount,
            color: "text-orange-600",
          },
          {
            label: "Within a Week",
            value: isLoading ? "-" : withinWeekCount,
            color: "text-blue-600",
          },
          {
            label: "Within a Month",
            value: isLoading ? "-" : withinMonthCount,
            color: "text-purple-600",
          },
        ]}
      />

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        <Select
          value={urgencyFilter}
          onValueChange={(v) => setUrgencyFilter(v as UrgencyFilter)}
        >
          <SelectTrigger className="w-[180px]">
            <SelectValue placeholder="Urgency" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Urgencies</SelectItem>
            <SelectItem value="IMMEDIATELY">Immediately</SelectItem>
            <SelectItem value="WITHIN_A_WEEK">Within a Week</SelectItem>
            <SelectItem value="WITHIN_A_MONTH">Within a Month</SelectItem>
          </SelectContent>
        </Select>

        <Select
          value={signalFilter}
          onValueChange={(v) => setSignalFilter(v as SignalFilter)}
        >
          <SelectTrigger className="w-[160px]">
            <SelectValue placeholder="Signal" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All Signals</SelectItem>
            <SelectItem value="BULLISH">Bullish</SelectItem>
            <SelectItem value="BEARISH">Bearish</SelectItem>
          </SelectContent>
        </Select>

        <div className="relative flex-1 min-w-[200px] max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search by ticker..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
      </div>

      {/* Detail Panel */}
      {selectedAlert && (
        <DetailPanel
          alert={selectedAlert}
          onClose={() => setSelectedAlert(null)}
        />
      )}

      {/* Card Grid / Loading / Empty */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} className="h-48 rounded-xl" />
          ))}
        </div>
      ) : filteredAlerts.length === 0 ? (
        <EmptyState
          icon={<CheckCircle2 className="h-12 w-12" />}
          title="No approved alerts"
          description={
            search || urgencyFilter !== "all" || signalFilter !== "all"
              ? "Try adjusting your filters or search term."
              : "Approved alerts will appear here once the FM takes action."
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
          {filteredAlerts.map((alert) => (
            <ApprovedCard
              key={alert.id}
              alert={alert}
              onClick={() => handleCardClick(alert)}
            />
          ))}
        </div>
      )}
    </div>
  );
}
