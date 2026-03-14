"use client";

import { cn } from "@/lib/utils";

interface IndicatorMetric {
  key: string;
  label: string;
  count: number;
  total: number;
  pct: number;
  invert?: boolean;
  placeholder?: boolean;
}

interface IndicatorRowProps {
  metric: IndicatorMetric;
}

export function IndicatorRow({ metric }: IndicatorRowProps) {
  const { label, count, total, pct, invert, placeholder } = metric;

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
    <div className="flex items-center gap-3 py-2.5 px-3 rounded-lg hover:bg-slate-50 transition-colors">
      {/* Label */}
      <span className="text-sm text-slate-600 w-[40%] truncate" title={label}>
        {label}
      </span>
      {/* Bar */}
      <div className="w-[30%] bg-slate-100 rounded-full h-2">
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
    </div>
  );
}
