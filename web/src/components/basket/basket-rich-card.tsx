"use client";

import { cn } from "@/lib/utils";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { BasketLiveItem } from "@/lib/basket-types";

interface BasketRichCardProps {
  basket: BasketLiveItem;
  period: string;
  isSelected: boolean;
  onClick: () => void;
}

/** Format value in lakhs notation: 5.25L, 12.80L, 1.05Cr */
function formatLakhs(value: number | null | undefined): string {
  if (value == null) return "--";
  if (value >= 1_00_00_000) return `${(value / 1_00_00_000).toFixed(2)}Cr`;
  if (value >= 1_00_000) return `${(value / 1_00_000).toFixed(2)}L`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
}

/** Determine a left-border color based on basket name keywords */
function getBorderColor(name: string): string {
  const lower = name.toLowerCase();
  if (lower.includes("bank") || lower.includes("financ")) return "border-l-blue-500";
  if (lower.includes("it") || lower.includes("tech") || lower.includes("digital")) return "border-l-violet-500";
  if (lower.includes("pharma") || lower.includes("health")) return "border-l-pink-500";
  if (lower.includes("energy") || lower.includes("oil") || lower.includes("gas")) return "border-l-amber-500";
  if (lower.includes("auto") || lower.includes("ev") || lower.includes("mobility")) return "border-l-cyan-500";
  if (lower.includes("fmcg") || lower.includes("consumer") || lower.includes("consumption")) return "border-l-green-500";
  if (lower.includes("metal") || lower.includes("commodit")) return "border-l-slate-500";
  if (lower.includes("realty") || lower.includes("infra") || lower.includes("housing")) return "border-l-orange-500";
  if (lower.includes("media")) return "border-l-fuchsia-500";
  if (lower.includes("defence") || lower.includes("railway")) return "border-l-emerald-500";
  return "border-l-teal-500";
}

/** Format date string to short format */
function formatShortDate(dateStr: string | null | undefined): string {
  if (!dateStr) return "--";
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });
  } catch {
    return dateStr;
  }
}

export function BasketRichCard({ basket, period, isSelected, onClick }: BasketRichCardProps) {
  const pk = period.toLowerCase();
  const ratioReturn = basket.ratio_returns?.[pk] ?? null;
  const indexReturn = basket.index_returns?.[pk] ?? null;
  const isExited = Boolean(basket.exit_date);
  const borderColor = getBorderColor(basket.name);

  // Compute P&L percentage from portfolio size vs worth
  const pnlPct = basket.portfolio_size && basket.portfolio_worth
    ? ((basket.portfolio_worth - basket.portfolio_size) / basket.portfolio_size) * 100
    : null;

  // Top constituents (first 4 tickers)
  const topConstituents = basket.constituents.slice(0, 4);
  const moreCount = basket.num_constituents - topConstituents.length;

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "bg-white rounded-xl border border-slate-200 border-l-4 p-4 text-left",
        "transition-all hover:shadow-md cursor-pointer w-full",
        borderColor,
        isSelected && "ring-2 ring-teal-500 shadow-md"
      )}
    >
      {/* Top row: Name + Status */}
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-bold text-slate-800 leading-tight truncate flex-1">
          {basket.name}
        </h3>
        <span
          className={cn(
            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
            isExited
              ? "bg-slate-100 text-slate-600"
              : "bg-emerald-100 text-emerald-700"
          )}
        >
          {isExited ? "STOPPED" : "ACTIVE"}
        </span>
      </div>

      {/* Description */}
      {basket.description && (
        <p className="text-[11px] text-muted-foreground mt-0.5 line-clamp-1">
          {basket.description}
        </p>
      )}

      {/* Metrics grid */}
      <div className="grid grid-cols-3 gap-3 mt-3">
        {/* Size */}
        <div>
          <p className="text-[10px] text-muted-foreground">Size</p>
          <p className="text-sm font-semibold font-mono text-slate-700">
            {basket.portfolio_size ? `\u20B9${formatLakhs(basket.portfolio_size)}` : "--"}
          </p>
        </div>
        {/* Worth */}
        <div>
          <p className="text-[10px] text-muted-foreground">Worth</p>
          <p className="text-sm font-semibold font-mono text-slate-700">
            {basket.portfolio_worth ? `\u20B9${formatLakhs(basket.portfolio_worth)}` : "--"}
          </p>
        </div>
        {/* P&L */}
        <div>
          <p className="text-[10px] text-muted-foreground">P&L</p>
          <p
            className={cn(
              "text-sm font-semibold font-mono",
              pnlPct == null
                ? "text-slate-400"
                : pnlPct >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
            )}
          >
            {pnlPct != null
              ? `${pnlPct >= 0 ? "+" : ""}${pnlPct.toFixed(1)}%`
              : "--"}
          </p>
        </div>
      </div>

      {/* Constituents */}
      <div className="mt-3">
        <p className="text-[10px] text-muted-foreground mb-1">
          {basket.num_constituents} stock{basket.num_constituents !== 1 ? "s" : ""}
        </p>
        <div className="flex flex-wrap gap-1">
          {topConstituents.map((c) => (
            <span
              key={c.ticker}
              className="bg-slate-100 rounded px-1.5 py-0.5 text-[10px] font-mono text-slate-600"
            >
              {c.ticker}
            </span>
          ))}
          {moreCount > 0 && (
            <span className="bg-slate-50 rounded px-1.5 py-0.5 text-[10px] text-muted-foreground">
              +{moreCount} more
            </span>
          )}
        </div>
      </div>

      {/* Bottom row: Ratio return + Execution date */}
      <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100">
        {/* Ratio return vs base */}
        <div className="flex items-center gap-1">
          {ratioReturn != null ? (
            <>
              {ratioReturn >= 0 ? (
                <TrendingUp className="h-3 w-3 text-emerald-600" />
              ) : (
                <TrendingDown className="h-3 w-3 text-red-600" />
              )}
              <span
                className={cn(
                  "text-[10px] font-mono font-medium",
                  ratioReturn >= 0 ? "text-emerald-600" : "text-red-600"
                )}
              >
                vs {basket.benchmark} ({period}): {ratioReturn >= 0 ? "+" : ""}{ratioReturn.toFixed(1)}%
              </span>
            </>
          ) : indexReturn != null ? (
            <span
              className={cn(
                "text-[10px] font-mono",
                indexReturn >= 0 ? "text-emerald-600" : "text-red-600"
              )}
            >
              {period}: {indexReturn >= 0 ? "+" : ""}{indexReturn.toFixed(1)}%
            </span>
          ) : (
            <span className="text-[10px] text-muted-foreground">No data for {period}</span>
          )}
        </div>

        {/* Execution date */}
        {basket.execution_date && (
          <span className="text-[10px] text-muted-foreground">
            {formatShortDate(basket.execution_date)}
          </span>
        )}
      </div>
    </button>
  );
}
