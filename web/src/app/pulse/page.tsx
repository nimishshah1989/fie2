"use client";

import { useMemo, useState } from "react";
import { useIndices } from "@/hooks/use-indices";
import { IndexTable } from "@/components/index-table";
import { SignalHeatmap } from "@/components/signal-heatmap";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BASE_INDEX_OPTIONS, PERIOD_OPTIONS, getSector, SECTOR_ORDER, NON_NSE_KEYS } from "@/lib/constants";
import { formatTimestamp } from "@/lib/utils";
import { Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import type { LiveIndex } from "@/lib/types";

type PulseTab = "nse" | "global";

/** Check if an index item belongs to the BSE & Global category */
function isGlobalItem(idx: LiveIndex): boolean {
  const key = idx.index_name?.toUpperCase() ?? "";
  if (NON_NSE_KEYS.has(key)) return true;
  // Also check by display name / sector
  const name = idx.nse_name || idx.index_name;
  const sector = getSector(name);
  return sector === "BSE" || sector === "Commodities" || sector === "Currency";
}

export default function PulsePage() {
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState("1M");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [activeTab, setActiveTab] = useState<PulseTab>("nse");

  const { data, error, isLoading } = useIndices(base);

  // Split indices into NSE and Global
  const { nseIndices, globalIndices } = useMemo(() => {
    const nse: LiveIndex[] = [];
    const global: LiveIndex[] = [];
    for (const idx of data.indices) {
      if (isGlobalItem(idx)) {
        global.push(idx);
      } else {
        nse.push(idx);
      }
    }
    return { nseIndices: nse, globalIndices: global };
  }, [data.indices]);

  const activeIndices = activeTab === "nse" ? nseIndices : globalIndices;

  // Compute unique sectors from active tab's data
  const sectors = useMemo(() => {
    if (!activeIndices.length) return [];
    const sectorSet = new Set<string>();
    for (const idx of activeIndices) {
      const name = idx.nse_name || idx.index_name;
      sectorSet.add(getSector(name));
    }
    return SECTOR_ORDER.filter((s) => sectorSet.has(s));
  }, [activeIndices]);

  // Reset sector filter when switching tabs
  const handleTabChange = (tab: PulseTab) => {
    setActiveTab(tab);
    setSectorFilter("all");
  };

  // Filter indices by selected sector
  const filteredIndices = useMemo(() => {
    if (sectorFilter === "all") return activeIndices;
    return activeIndices.filter((idx) => {
      const name = idx.nse_name || idx.index_name;
      return getSector(name) === sectorFilter;
    });
  }, [activeIndices, sectorFilter]);

  return (
    <div className="space-y-4 sm:space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Activity className="size-5 sm:size-6 text-blue-600" />
          <h1 className="text-xl sm:text-2xl font-bold text-foreground">Market Pulse</h1>
        </div>
        <p className="text-xs sm:text-sm text-muted-foreground mt-1">
          Live index signals, sector analysis, and global benchmarks
        </p>
      </div>

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-border">
        <button
          type="button"
          onClick={() => handleTabChange("nse")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "nse"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          )}
        >
          NSE Indices
          {nseIndices.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({nseIndices.length})</span>
          )}
        </button>
        <button
          type="button"
          onClick={() => handleTabChange("global")}
          className={cn(
            "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
            activeTab === "global"
              ? "border-blue-600 text-blue-600"
              : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
          )}
        >
          BSE & Global
          {globalIndices.length > 0 && (
            <span className="ml-1.5 text-xs text-muted-foreground">({globalIndices.length})</span>
          )}
        </button>
      </div>

      {/* Filters Row */}
      <div className="grid grid-cols-2 sm:flex sm:flex-wrap sm:items-center gap-2 sm:gap-3">
        {/* Base Index */}
        <Select value={base} onValueChange={setBase}>
          <SelectTrigger className="w-full sm:w-[160px]">
            <SelectValue placeholder="Base Index" />
          </SelectTrigger>
          <SelectContent>
            {BASE_INDEX_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>
                {opt}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Period */}
        <Select value={period} onValueChange={setPeriod}>
          <SelectTrigger className="w-full sm:w-[100px]">
            <SelectValue placeholder="Period" />
          </SelectTrigger>
          <SelectContent>
            {PERIOD_OPTIONS.map((opt) => (
              <SelectItem key={opt} value={opt}>
                {opt}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Sector */}
        {sectors.length > 1 && (
          <Select value={sectorFilter} onValueChange={setSectorFilter}>
            <SelectTrigger className="w-full col-span-2 sm:w-[200px]">
              <SelectValue placeholder="Sector" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Sectors</SelectItem>
              {sectors.map((sector) => (
                <SelectItem key={sector} value={sector}>
                  {sector}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      {/* Info Caption */}
      {!isLoading && activeIndices.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {filteredIndices.length} {activeTab === "nse" ? "indices" : "instruments"}
          {sectorFilter !== "all" ? ` in ${sectorFilter}` : ""}
          {" "}&bull;{" "}
          Last refreshed {formatTimestamp(data.timestamp)}
        </p>
      )}

      {/* Error */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          Failed to load index data. Please try again later.
          {data.error && <span className="block mt-1 text-xs">{data.error}</span>}
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-32 rounded-xl" />
          <Skeleton className="h-[400px] rounded-xl" />
        </div>
      )}

      {/* Content */}
      {!isLoading && !error && activeIndices.length > 0 && (
        <>
          {/* Signal Heatmap — only for NSE tab */}
          {activeTab === "nse" && (
            <div className="rounded-lg border bg-card p-4">
              <SignalHeatmap indices={nseIndices} period={period} />
            </div>
          )}

          <hr className="border-border" />

          {/* Index Table */}
          <IndexTable indices={filteredIndices} period={period} timestamp={data.timestamp} />
        </>
      )}

      {/* Empty state */}
      {!isLoading && !error && activeIndices.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Activity className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">
            {activeTab === "global"
              ? "No BSE & Global data yet"
              : "No index data available"}
          </h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
            {activeTab === "global"
              ? "BSE indices, commodities, and currency data will appear after the next data backfill."
              : "Index data will appear here once the backend is connected."}
          </p>
        </div>
      )}
    </div>
  );
}
