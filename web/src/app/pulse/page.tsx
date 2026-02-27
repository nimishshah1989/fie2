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
import { BASE_INDEX_OPTIONS, PERIOD_OPTIONS, getSector, SECTOR_ORDER } from "@/lib/constants";
import { formatTimestamp } from "@/lib/utils";
import { Activity } from "lucide-react";

export default function PulsePage() {
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState("1M");
  const [sectorFilter, setSectorFilter] = useState("all");

  const { data, error, isLoading } = useIndices(base);

  // Compute unique sectors from the data
  const sectors = useMemo(() => {
    if (!data.indices.length) return [];
    const sectorSet = new Set<string>();
    for (const idx of data.indices) {
      const name = idx.nse_name || idx.index_name;
      sectorSet.add(getSector(name));
    }
    // Sort by SECTOR_ORDER
    return SECTOR_ORDER.filter((s) => sectorSet.has(s));
  }, [data.indices]);

  // Filter indices by selected sector
  const filteredIndices = useMemo(() => {
    if (sectorFilter === "all") return data.indices;
    return data.indices.filter((idx) => {
      const name = idx.nse_name || idx.index_name;
      return getSector(name) === sectorFilter;
    });
  }, [data.indices, sectorFilter]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Activity className="size-6 text-blue-600" />
          <h1 className="text-2xl font-bold text-foreground">Market Pulse</h1>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Live NSE index signals and sector analysis
        </p>
      </div>

      {/* Filters Row */}
      <div className="flex flex-wrap items-center gap-3">
        {/* Base Index */}
        <Select value={base} onValueChange={setBase}>
          <SelectTrigger className="w-[160px]">
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
          <SelectTrigger className="w-[100px]">
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
        <Select value={sectorFilter} onValueChange={setSectorFilter}>
          <SelectTrigger className="w-[200px]">
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
      </div>

      {/* Info Caption */}
      {!isLoading && data.indices.length > 0 && (
        <p className="text-xs text-muted-foreground">
          {filteredIndices.length} indices
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
      {!isLoading && !error && data.indices.length > 0 && (
        <>
          {/* Signal Heatmap */}
          <div className="rounded-lg border bg-card p-4">
            <SignalHeatmap indices={data.indices} />
          </div>

          <hr className="border-border" />

          {/* Index Table */}
          <IndexTable indices={filteredIndices} period={period} />
        </>
      )}

      {/* Empty state when no error but no data */}
      {!isLoading && !error && data.indices.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <Activity className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <h3 className="text-lg font-semibold text-foreground">No index data available</h3>
          <p className="text-sm text-muted-foreground mt-1 max-w-sm">
            Index data will appear here once the backend is connected.
          </p>
        </div>
      )}
    </div>
  );
}
