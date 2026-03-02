"use client";

import { cn } from "@/lib/utils";
import type { BasketLiveItem } from "@/lib/basket-types";

interface BasketCardGridProps {
  baskets: BasketLiveItem[];
  period: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

/** Returns Tailwind classes based on ratio return magnitude — matches signal-heatmap.tsx */
function getIntensityStyle(ratioReturn: number | null): string {
  if (ratioReturn == null) return "bg-slate-50 text-slate-600 border-slate-200";

  const abs = Math.abs(ratioReturn);

  if (ratioReturn >= 0) {
    if (abs >= 10) return "bg-emerald-400 text-white border-emerald-500";
    if (abs >= 7) return "bg-emerald-300 text-emerald-900 border-emerald-400";
    if (abs >= 4) return "bg-emerald-200 text-emerald-900 border-emerald-300";
    if (abs >= 2) return "bg-emerald-100 text-emerald-800 border-emerald-300";
    return "bg-emerald-50 text-emerald-700 border-emerald-200";
  } else {
    if (abs >= 10) return "bg-red-400 text-white border-red-500";
    if (abs >= 7) return "bg-red-300 text-red-900 border-red-400";
    if (abs >= 4) return "bg-red-200 text-red-900 border-red-300";
    if (abs >= 2) return "bg-red-100 text-red-800 border-red-300";
    return "bg-red-50 text-red-700 border-red-200";
  }
}

export function BasketCardGrid({ baskets, period, selectedId, onSelect }: BasketCardGridProps) {
  const pk = period.toLowerCase();

  if (baskets.length === 0) return null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3">
      {baskets.map((basket) => {
        const ratioReturn = basket.ratio_returns?.[pk] ?? null;
        const indexReturn = basket.index_returns?.[pk] ?? null;
        const style = getIntensityStyle(ratioReturn);
        const isSelected = selectedId === basket.id;

        return (
          <button
            key={basket.id}
            type="button"
            onClick={() => onSelect(basket.id)}
            className={cn(
              "rounded-lg border px-3 py-3 text-left transition-all hover:shadow-md cursor-pointer",
              style,
              isSelected && "ring-2 ring-blue-500 shadow-md"
            )}
          >
            <div className="text-sm font-semibold leading-tight truncate">
              {basket.name}
            </div>
            <div className="text-[10px] opacity-70 mt-0.5">
              {basket.num_constituents} stocks
            </div>

            {basket.current_value != null && (
              <div className="text-xs font-mono mt-1.5">
                {basket.current_value.toLocaleString("en-IN", {
                  minimumFractionDigits: 2,
                  maximumFractionDigits: 2,
                })}
              </div>
            )}

            <div className="flex items-center gap-2 mt-1">
              {ratioReturn != null && (
                <span className="text-[10px] font-mono opacity-80" title="Ratio return vs base">
                  R: {ratioReturn >= 0 ? "+" : ""}{ratioReturn.toFixed(1)}%
                </span>
              )}
              {indexReturn != null && (
                <span className="text-[10px] font-mono opacity-60" title="Absolute return">
                  {indexReturn >= 0 ? "+" : ""}{indexReturn.toFixed(1)}%
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
