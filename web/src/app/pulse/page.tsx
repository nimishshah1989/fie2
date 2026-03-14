"use client";

import { useMemo, useState } from "react";
import { useIndices } from "@/hooks/use-indices";
import { IndexTable } from "@/components/index-table";
import { SignalHeatmap } from "@/components/signal-heatmap";
import { FixedIncomeTable } from "@/components/fixed-income-table";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { BASE_INDEX_OPTIONS, PERIOD_OPTIONS } from "@/lib/constants";
import { formatTimestamp } from "@/lib/utils";
import { Activity } from "lucide-react";
import { PageInfo } from "@/components/page-info";
import { cn } from "@/lib/utils";
import type { LiveIndex } from "@/lib/types";

type PulseTab = "broad" | "sectoral" | "thematic" | "global" | "fixed_income";

const TABS: { key: PulseTab; label: string }[] = [
  { key: "broad",       label: "Broad Market" },
  { key: "sectoral",    label: "Sectoral" },
  { key: "thematic",    label: "Thematic" },
  { key: "global",      label: "BSE & Global" },
  { key: "fixed_income", label: "Fixed Income" },
];

function getCategory(idx: LiveIndex): PulseTab {
  const cat = idx.category;
  if (cat === "sectoral") return "sectoral";
  if (cat === "thematic") return "thematic";
  if (cat === "global") return "global";
  if (cat === "fixed_income") return "fixed_income";
  return "broad";
}

export default function PulsePage() {
  const [base, setBase] = useState("NIFTY");
  const [period, setPeriod] = useState("1M");
  const [activeTab, setActiveTab] = useState<PulseTab>("broad");

  const { data, error, isLoading } = useIndices(base);

  // Group indices by category
  const grouped = useMemo(() => {
    const map: Record<PulseTab, LiveIndex[]> = {
      broad: [], sectoral: [], thematic: [], global: [], fixed_income: [],
    };
    for (const idx of data.indices) {
      const cat = getCategory(idx);
      map[cat].push(idx);
    }
    return map;
  }, [data.indices]);

  const activeIndices = grouped[activeTab];
  const showHeatmap = activeTab === "broad" || activeTab === "sectoral" || activeTab === "thematic";

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

      <PageInfo>
        Live NSE index data with ratio analysis versus a benchmark index. Covers 79 indices across broad market, sectoral,
        thematic, BSE/global, and fixed income categories. Ratio returns show relative outperformance —
        positive means the index outperformed the benchmark over that period.
      </PageInfo>

      {/* Tab Bar */}
      <div className="flex items-center gap-1 border-b border-border overflow-x-auto">
        {TABS.map(({ key, label }) => (
          <button
            key={key}
            type="button"
            onClick={() => setActiveTab(key)}
            className={cn(
              "px-4 py-2 text-sm font-medium border-b-2 transition-colors whitespace-nowrap",
              activeTab === key
                ? "border-teal-600 text-teal-600"
                : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
            )}
          >
            {label}
            {grouped[key].length > 0 && (
              <span className="ml-1.5 text-xs text-muted-foreground">({grouped[key].length})</span>
            )}
          </button>
        ))}
      </div>

      {/* Fixed Income tab */}
      {activeTab === "fixed_income" && (
        <FixedIncomeTable indices={grouped.fixed_income} />
      )}

      {/* Controls for data tabs */}
      {activeTab !== "fixed_income" && (
        <>
          {/* Filters Row */}
          <div className="flex flex-wrap items-center gap-2 sm:gap-3">
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
          </div>

          {/* Info Caption */}
          {!isLoading && activeIndices.length > 0 && (
            <p className="text-xs text-muted-foreground">
              {activeIndices.length} {activeTab === "global" ? "instruments" : "indices"} &bull;{" "}
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
              {showHeatmap && (
                <div className="rounded-lg border bg-card p-4">
                  <SignalHeatmap indices={activeIndices} period={period} />
                </div>
              )}
              <hr className="border-border" />
              <IndexTable indices={activeIndices} period={period} timestamp={data.timestamp} />
            </>
          )}

          {/* Empty state */}
          {!isLoading && !error && activeIndices.length === 0 && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Activity className="h-12 w-12 text-muted-foreground/50 mb-4" />
              <h3 className="text-lg font-semibold text-foreground">No data available</h3>
              <p className="text-sm text-muted-foreground mt-1 max-w-sm">
                Index data will appear here once the backend is connected and prices are loaded.
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
