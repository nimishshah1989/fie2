"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SignalChip } from "@/components/signal-chip";
import { formatPrice, formatPct, cn } from "@/lib/utils";
import type { ActionableAlert } from "@/lib/types";
import { TrendingUp, TrendingDown, Target, ShieldAlert } from "lucide-react";

interface ActionableCardProps {
  alert: ActionableAlert;
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

export function ActionableCard({ alert }: ActionableCardProps) {
  const isProfit = alert.pnl_pct >= 0;
  const isTPHit = alert.trigger_type === "TP_HIT";
  const borderColor = isTPHit ? "border-l-emerald-500" : "border-l-red-500";
  const actionCall = alert.action?.action_call ?? "";
  const actionStyle =
    actionColors[actionCall.toUpperCase()] ??
    "bg-slate-100 text-slate-600 border-slate-200";

  return (
    <Card
      className={cn(
        "gap-0 rounded-xl border bg-card p-4 shadow-sm border-l-4 py-0 overflow-hidden",
        borderColor
      )}
    >
      <CardContent className="p-4 px-3 space-y-3">
        {/* Header: Ticker + Signal + Action + Trigger badge */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-foreground">
              {alert.ticker}
            </span>
            <SignalChip signal={alert.signal_direction} />
          </div>
          <div className="flex items-center gap-1.5">
            {actionCall && (
              <Badge variant="outline" className={actionStyle}>
                {actionCall.toUpperCase()}
              </Badge>
            )}
          </div>
        </div>

        {/* Trigger Type Badge */}
        <div className="flex items-center gap-2">
          {isTPHit ? (
            <div className="flex items-center gap-1.5 rounded-md bg-emerald-50 border border-emerald-200 px-2.5 py-1">
              <Target className="size-3.5 text-emerald-600" />
              <span className="text-xs font-semibold text-emerald-700">
                Target Hit
              </span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-md bg-red-50 border border-red-200 px-2.5 py-1">
              <ShieldAlert className="size-3.5 text-red-600" />
              <span className="text-xs font-semibold text-red-700">
                Stop Loss Hit
              </span>
            </div>
          )}
          <span className="text-xs text-muted-foreground ml-auto">
            {alert.days_since != null ? `${alert.days_since}d ago` : ""}
          </span>
        </div>

        {/* Price details */}
        <div className="grid grid-cols-2 gap-2 text-sm">
          <div>
            <span className="text-xs text-muted-foreground">Entry</span>
            <div className="font-medium">{formatPrice(alert.entry_price)}</div>
          </div>
          <div>
            <span className="text-xs text-muted-foreground">Current</span>
            <div className="font-medium">{formatPrice(alert.current_price)}</div>
          </div>
          {alert.stop_loss != null && (
            <div>
              <span className="text-xs text-muted-foreground">Stop Loss</span>
              <div className="font-medium text-red-600">
                {formatPrice(alert.stop_loss)}
              </div>
            </div>
          )}
          {alert.target_price != null && (
            <div>
              <span className="text-xs text-muted-foreground">Target</span>
              <div className="font-medium text-emerald-600">
                {formatPrice(alert.target_price)}
              </div>
            </div>
          )}
        </div>

        {/* P&L */}
        <div className="flex items-center justify-between rounded-lg bg-muted/50 px-3 py-2">
          <div className="flex items-center gap-1.5">
            {isProfit ? (
              <TrendingUp className="size-4 text-emerald-600" />
            ) : (
              <TrendingDown className="size-4 text-red-600" />
            )}
            <span className="text-xs text-muted-foreground">P&L</span>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={cn(
                "text-sm font-bold",
                isProfit ? "text-emerald-600" : "text-red-600"
              )}
            >
              {formatPct(alert.pnl_pct)}
            </span>
            <span
              className={cn(
                "text-xs",
                isProfit ? "text-emerald-500" : "text-red-500"
              )}
            >
              ({isProfit ? "+" : ""}
              {formatPrice(alert.pnl_abs)})
            </span>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
