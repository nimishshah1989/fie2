"use client";

import type { Alert } from "@/lib/types";
import { cn, formatPrice, formatTimestamp } from "@/lib/utils";
import { SignalChip } from "@/components/signal-chip";
import { OhlcvStrip } from "@/components/ohlcv-strip";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle } from "lucide-react";

interface AlertCardCompactProps {
  alert: Alert;
  onApprove: (id: number) => void;
  onDeny: (id: number) => void;
}

const borderColorMap: Record<string, string> = {
  BULLISH: "border-l-emerald-500",
  BEARISH: "border-l-red-500",
  NEUTRAL: "border-l-slate-400",
};

export function AlertCardCompact({
  alert,
  onApprove,
  onDeny,
}: AlertCardCompactProps) {
  const borderColor = borderColorMap[alert.signal_direction] ?? "border-l-slate-400";

  return (
    <div
      className={cn(
        "rounded-xl border border-l-4 bg-card shadow-sm hover:shadow-md transition-shadow p-4 flex flex-col gap-3",
        borderColor
      )}
    >
      {/* Header: Ticker + Signal + Interval */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-base text-foreground">
            {alert.ticker}
          </span>
          <SignalChip signal={alert.signal_direction} />
        </div>
        <span className="text-xs font-medium text-muted-foreground bg-muted rounded-md px-2 py-0.5">
          {alert.interval}
        </span>
      </div>

      {/* Alert name, exchange, time */}
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        <span className="truncate mr-2">{alert.alert_name}</span>
        <div className="flex items-center gap-2 shrink-0">
          <span className="uppercase">{alert.exchange}</span>
          <span>{formatTimestamp(alert.received_at)}</span>
        </div>
      </div>

      {/* OHLCV Strip */}
      <OhlcvStrip
        open={alert.price_open}
        high={alert.price_high}
        low={alert.price_low}
        close={alert.price_close}
        volume={alert.volume}
      />

      {/* Price at alert */}
      {alert.price_at_alert != null && (
        <div className="rounded-md bg-blue-50 border border-blue-100 px-3 py-1.5 flex items-center justify-between">
          <span className="text-xs font-medium text-blue-700">Price at Alert</span>
          <span className="text-sm font-bold text-blue-900">
            {formatPrice(alert.price_at_alert)}
          </span>
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex items-center gap-2 pt-1">
        <Button
          size="sm"
          className="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white"
          onClick={() => onApprove(alert.id)}
        >
          <CheckCircle2 className="h-3.5 w-3.5" />
          Approve
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1 border-red-300 text-red-600 hover:bg-red-50 hover:text-red-700"
          onClick={() => onDeny(alert.id)}
        >
          <XCircle className="h-3.5 w-3.5" />
          Deny
        </Button>
      </div>
    </div>
  );
}
