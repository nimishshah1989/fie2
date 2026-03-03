"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import { SECTOR_COLORS } from "@/lib/constants";
import { SectorResultCard, type SectorResult } from "./sector-result-card";

interface RecommendationResultsProps {
  qualifyingSectors: SectorResult[];
  nonQualifyingSectors: SectorResult[];
  base: string;
  period: string;
  threshold: number;
}

const PERIOD_LABELS: Record<string, string> = {
  "1w": "1W",
  "1m": "1M",
  "3m": "3M",
  "6m": "6M",
  "12m": "12M",
};

export function RecommendationResults({
  qualifyingSectors,
  nonQualifyingSectors,
  base,
  period,
  threshold,
}: RecommendationResultsProps) {
  const [showNonQualifying, setShowNonQualifying] = useState(false);
  const totalSelected = qualifyingSectors.length + nonQualifyingSectors.length;
  const periodLabel = PERIOD_LABELS[period] || period;

  return (
    <div className="space-y-4">
      {/* Summary Bar */}
      <div className="rounded-lg border bg-gray-50 px-4 py-2.5">
        <p className="text-sm font-medium text-foreground">
          <span className="text-emerald-600 font-bold">{qualifyingSectors.length}</span>
          {" "}of{" "}
          <span className="font-bold">{totalSelected}</span>
          {" "}sectors qualify at{" "}
          <span className="font-mono font-bold">&gt;{threshold}%</span>
          {" "}for{" "}
          <span className="font-bold">{periodLabel}</span>
          {" "}vs{" "}
          <span className="font-bold">{base}</span>
        </p>
      </div>

      {/* Qualifying Sectors */}
      {qualifyingSectors.length > 0 ? (
        <div className="space-y-3">
          {qualifyingSectors.map((sector) => (
            <SectorResultCard key={sector.sector_key} sector={sector} threshold={threshold} />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-10 text-center">
          <p className="text-sm text-muted-foreground">
            No sectors exceeded the {threshold}% threshold for {periodLabel}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Try lowering the threshold or selecting different sectors
          </p>
        </div>
      )}

      {/* Non-qualifying Sectors */}
      {nonQualifyingSectors.length > 0 && (
        <div className="space-y-2">
          <button
            onClick={() => setShowNonQualifying(!showNonQualifying)}
            className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground hover:text-foreground transition-colors"
          >
            {showNonQualifying ? (
              <ChevronDown className="h-3.5 w-3.5" />
            ) : (
              <ChevronRight className="h-3.5 w-3.5" />
            )}
            Non-qualifying sectors ({nonQualifyingSectors.length})
          </button>

          {showNonQualifying && (
            <div className="flex flex-wrap gap-2">
              {nonQualifyingSectors.map((sector) => {
                const colors = SECTOR_COLORS[sector.sector_key];
                return (
                  <div
                    key={sector.sector_key}
                    className={cn(
                      "rounded-md border px-3 py-1.5 text-xs",
                      colors ? `${colors.bg} ${colors.border}` : "bg-gray-50 border-gray-200"
                    )}
                  >
                    <span className={cn("font-medium", colors?.text || "text-muted-foreground")}>
                      {sector.sector_name}
                    </span>
                    <span className={cn(
                      "ml-2 font-mono",
                      sector.ratio_return != null && sector.ratio_return >= 0 ? "text-emerald-600" : "text-red-600"
                    )}>
                      {sector.ratio_return != null
                        ? `${sector.ratio_return >= 0 ? "+" : ""}${sector.ratio_return.toFixed(2)}%`
                        : "---"}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
