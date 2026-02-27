"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SignalChip } from "@/components/signal-chip";
import { formatPrice, formatPct, cn } from "@/lib/utils";
import type { PerformanceAlert } from "@/lib/types";
import { TrendingUp, TrendingDown, ArrowRightLeft } from "lucide-react";

interface PerformanceCardProps {
  alert: PerformanceAlert;
}

const actionColors: Record<string, string> = {
  BUY: "bg-emerald-100 text-emerald-700 border-emerald-200",
  SELL: "bg-red-100 text-red-700 border-red-200",
  HOLD: "bg-slate-100 text-slate-600 border-slate-200",
  RATIO: "bg-violet-100 text-violet-700 border-violet-200",
  ACCUMULATE: "bg-emerald-100 text-emerald-700 border-emerald-200",
  REDUCE: "bg-amber-100 text-amber-700 border-amber-200",
  SWITCH: "bg-blue-100 text-blue-700 border-blue-200",
  WATCH: "bg-slate-100 text-slate-600 border-slate-200",
};

export function PerformanceCard({ alert }: PerformanceCardProps) {
  const returnPct = alert.return_pct ?? 0;
  const isPositive = returnPct >= 0;
  const borderColor = isPositive ? "border-l-emerald-500" : "border-l-red-500";
  const actionCall = alert.action?.action_call ?? "";
  const actionStyle = actionColors[actionCall.toUpperCase()] ?? "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <Card
      className={cn(
        "gap-0 rounded-xl border bg-card p-4 shadow-sm border-l-4 py-0 overflow-hidden",
        borderColor
      )}
    >
      <CardContent className="p-4 px-3 space-y-3">
        {/* Header: Ticker + Signal + Action */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">
              {alert.ticker}
            </span>
            <SignalChip signal={alert.signal_direction} />
          </div>
          {actionCall && (
            <Badge variant="outline" className={actionStyle}>
              {actionCall.toUpperCase()}
            </Badge>
          )}
        </div>

        {/* Ratio trade info */}
        {alert.is_ratio_trade && alert.ratio_data && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <ArrowRightLeft className="size-3" />
            <span className="font-medium text-foreground">
              {alert.ratio_data.numerator_ticker}
            </span>
            <span>/</span>
            <span className="font-medium text-foreground">
              {alert.ratio_data.denominator_ticker}
            </span>
          </div>
        )}

        {/* Price row: Entry and Current */}
        <div className="flex items-center justify-between text-sm">
          <div>
            <span className="text-xs text-muted-foreground">Entry: </span>
            <span className="font-medium">{formatPrice(alert.entry_price)}</span>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">Current: </span>
            <span className="font-medium">{formatPrice(alert.current_price)}</span>
          </div>
        </div>

        {/* Return row: return_pct + days */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1.5">
            {isPositive ? (
              <TrendingUp className="size-4 text-emerald-600" />
            ) : (
              <TrendingDown className="size-4 text-red-600" />
            )}
            <span
              className={cn(
                "text-sm font-bold",
                isPositive ? "text-emerald-600" : "text-red-600"
              )}
            >
              {formatPct(alert.return_pct)}
            </span>
          </div>
          <span className="text-xs text-muted-foreground">
            {alert.days_since != null ? `${alert.days_since} days` : "---"}
          </span>
        </div>

        {/* Return absolute */}
        {alert.return_abs != null && (
          <div className="text-xs text-muted-foreground">
            Return: {alert.return_abs >= 0 ? "+" : ""}
            {formatPrice(Math.abs(alert.return_abs))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
