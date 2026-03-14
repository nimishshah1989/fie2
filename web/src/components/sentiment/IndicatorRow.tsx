"use client";

import { ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { SentimentMetric } from "@/lib/types";

interface IndicatorRowProps {
  metric: SentimentMetric;
  onClick?: (metric: SentimentMetric) => void;
}

export function IndicatorRow({ metric, onClick }: IndicatorRowProps) {
  const { label, count, total, pct, invert, placeholder, tickers } = metric;

  if (placeholder) {
    return (
      <div className="flex items-center gap-3 py-2.5 px-3 rounded-lg bg-slate-50 text-slate-400 text-sm">
        <span className="flex-1 truncate">{label}</span>
        <span className="text-xs italic">Not available</span>
      </div>
    );
  }

  const effectivePct = invert ? 100 - pct : pct;
  const threshold = 50;
  const clickable = !!onClick && (tickers?.length ?? 0) > 0;

  const barColor =
    effectivePct >= threshold
      ? "bg-emerald-500"
      : effectivePct >= threshold - 10
        ? "bg-amber-500"
        : "bg-red-500";

  const textColor =
    effectivePct >= threshold
      ? "text-emerald-600"
      : effectivePct >= threshold - 10
        ? "text-amber-600"
        : "text-red-600";

  return (
    <div
      className={cn(
        "flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors",
        clickable && "cursor-pointer group"
      )}
      onClick={() => clickable && onClick(metric)}
      role={clickable ? "button" : undefined}
      tabIndex={clickable ? 0 : undefined}
      onKeyDown={clickable ? (e) => { if (e.key === "Enter") onClick(metric); } : undefined}
    >
      {/* Label */}
      <span className="text-sm text-slate-600 w-[38%] truncate" title={label}>
        {label}
      </span>
      {/* Bar */}
      <div className="w-[28%] bg-slate-100 rounded-full h-2">
        <div
          className={cn("h-2 rounded-full transition-all", barColor)}
          style={{ width: `${Math.min(pct, 100)}%` }}
        />
      </div>
      {/* Count */}
      <span className="w-[12%] text-right text-sm font-mono tabular-nums text-slate-500">
        {count}/{total}
      </span>
      {/* Pct */}
      <span className={cn("w-[10%] text-right text-sm font-semibold font-mono tabular-nums", textColor)}>
        {pct.toFixed(1)}%
      </span>
      {/* Chevron */}
      {clickable ? (
        <ChevronRight className="h-4 w-4 text-slate-300 group-hover:text-slate-500 transition-colors flex-shrink-0" />
      ) : (
        <span className="w-4 flex-shrink-0" />
      )}
    </div>
  );
}
