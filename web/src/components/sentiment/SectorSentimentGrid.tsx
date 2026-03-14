"use client";

import { cn } from "@/lib/utils";
import type { SectorSentimentItem } from "@/hooks/use-sector-sentiment";

interface SectorSentimentGridProps {
  sectors: SectorSentimentItem[];
  onSelectSector: (sectorKey: string) => void;
}

function zoneColor(zone: string): {
  bar: string;
  text: string;
  badge: string;
  border: string;
} {
  switch (zone) {
    case "Strong":
      return { bar: "bg-emerald-500", text: "text-emerald-700", badge: "bg-emerald-100 text-emerald-700", border: "border-emerald-200" };
    case "Bullish":
      return { bar: "bg-emerald-400", text: "text-emerald-600", badge: "bg-emerald-50 text-emerald-600", border: "border-emerald-200" };
    case "Neutral":
      return { bar: "bg-slate-400", text: "text-slate-600", badge: "bg-slate-100 text-slate-600", border: "border-slate-200" };
    case "Weak":
      return { bar: "bg-amber-400", text: "text-amber-700", badge: "bg-amber-100 text-amber-700", border: "border-amber-200" };
    case "Bear":
      return { bar: "bg-red-400", text: "text-red-700", badge: "bg-red-100 text-red-700", border: "border-red-200" };
    default:
      return { bar: "bg-slate-400", text: "text-slate-600", badge: "bg-slate-100 text-slate-600", border: "border-slate-200" };
  }
}

function formatSectorName(name: string): string {
  return name
    .replace(/^NIFTY\s*/i, "")
    .replace(/\bINDEX\b/i, "")
    .trim() || name;
}

export function SectorSentimentGrid({ sectors, onSelectSector }: SectorSentimentGridProps) {
  if (sectors.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <p className="text-sm text-slate-400">
          No sector sentiment data available yet. Data is computed after market close.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
      {sectors.map((sector) => {
        const colors = zoneColor(sector.zone);
        const bullPct = sector.stock_count > 0
          ? Math.round((sector.bullish_count / sector.stock_count) * 100)
          : 0;

        return (
          <button
            key={sector.sector_key}
            type="button"
            onClick={() => onSelectSector(sector.sector_key)}
            className={cn(
              "bg-white rounded-xl border p-4 text-left transition-all hover:shadow-md",
              colors.border
            )}
          >
            {/* Sector Name + Zone Badge */}
            <div className="flex items-start justify-between gap-2 mb-3">
              <h3 className="text-sm font-semibold text-slate-800 leading-tight">
                {formatSectorName(sector.sector)}
              </h3>
              <span className={cn(
                "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                colors.badge
              )}>
                {sector.zone}
              </span>
            </div>

            {/* Score */}
            <div className="flex items-baseline gap-2 mb-3">
              <span className={cn("text-2xl font-bold font-mono tabular-nums", colors.text)}>
                {sector.avg_score.toFixed(1)}
              </span>
              <span className="text-xs text-slate-400">/100</span>
            </div>

            {/* Progress Bar */}
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden mb-3">
              <div
                className={cn("h-full rounded-full transition-all", colors.bar)}
                style={{ width: `${Math.min(sector.avg_score, 100)}%` }}
              />
            </div>

            {/* Stock Distribution */}
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span>{sector.stock_count} stocks</span>
              <span>
                <span className="text-emerald-600 font-medium">{bullPct}%</span> bullish
              </span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
