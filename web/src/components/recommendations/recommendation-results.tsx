"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  SectorResultCard,
  type QualifyingSector,
} from "./sector-result-card";

interface PeriodResult {
  qualifying_sectors: QualifyingSector[];
}

interface RecommendationResultsProps {
  results: Record<string, PeriodResult>;
  base: string;
}

const PERIOD_TABS = [
  { key: "1w", label: "1W" },
  { key: "1m", label: "1M" },
  { key: "3m", label: "3M" },
  { key: "6m", label: "6M" },
  { key: "12m", label: "12M" },
];

export function RecommendationResults({ results, base }: RecommendationResultsProps) {
  const [activePeriod, setActivePeriod] = useState("1m");

  const periodData = results[activePeriod];
  const qualifying = periodData?.qualifying_sectors ?? [];

  // Count total qualifying across all periods
  const totalCount = Object.values(results).reduce(
    (sum, r) => sum + (r.qualifying_sectors?.length ?? 0),
    0,
  );

  return (
    <div className="space-y-4">
      {/* Period Tabs */}
      <div className="flex gap-1 border-b border-border">
        {PERIOD_TABS.map((tab) => {
          const count = results[tab.key]?.qualifying_sectors?.length ?? 0;
          return (
            <button
              key={tab.key}
              onClick={() => setActivePeriod(tab.key)}
              className={cn(
                "px-3 py-2 text-sm font-medium border-b-2 transition-colors",
                activePeriod === tab.key
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-border"
              )}
            >
              {tab.label}
              {count > 0 && (
                <span className="ml-1.5 inline-flex items-center justify-center h-4 min-w-[16px] px-1 rounded-full bg-emerald-100 text-emerald-700 text-[10px] font-bold">
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Results for active period */}
      {qualifying.length > 0 ? (
        <div className="space-y-3">
          <p className="text-xs text-muted-foreground">
            {qualifying.length} sector{qualifying.length !== 1 ? "s" : ""} exceeded thresholds vs {base} for this period
          </p>
          {qualifying.map((sector) => (
            <SectorResultCard key={sector.sector_key} sector={sector} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <p className="text-sm text-muted-foreground">
            No sectors exceeded thresholds for the {PERIOD_TABS.find((t) => t.key === activePeriod)?.label} period
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Try lowering thresholds or check a different period tab
          </p>
        </div>
      )}

      {totalCount === 0 && (
        <p className="text-xs text-muted-foreground text-center pt-2">
          No qualifying sectors found across any period. Lower the thresholds to see results.
        </p>
      )}
    </div>
  );
}
