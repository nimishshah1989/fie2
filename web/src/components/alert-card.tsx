"use client";

import { cn } from "@/lib/utils";
import { formatPrice, formatTimestamp } from "@/lib/utils";
import { SignalChip } from "@/components/signal-chip";
import { OhlcvStrip } from "@/components/ohlcv-strip";
import { Button } from "@/components/ui/button";
import type { Alert } from "@/lib/types";

interface AlertCardProps {
  alert: Alert;
  onApprove?: (id: number) => void;
  onDeny?: (id: number) => void;
  showActions?: boolean;
}

const borderColor: Record<Alert["signal_direction"], string> = {
  BULLISH: "border-l-emerald-500",
  BEARISH: "border-l-red-500",
  NEUTRAL: "border-l-slate-400",
};

export function AlertCard({
  alert,
  onApprove,
  onDeny,
  showActions = false,
}: AlertCardProps) {
  return (
    <div
      className={cn(
        "bg-card rounded-xl border shadow-sm hover:shadow-md transition-shadow p-4 border-l-4 overflow-hidden",
        borderColor[alert.signal_direction]
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-lg font-bold">{alert.ticker}</span>
          <SignalChip signal={alert.signal_direction} />
        </div>
        <span className="text-xs text-muted-foreground">{alert.interval}</span>
      </div>

      {/* Metadata row */}
      <div className="flex items-center gap-2 mt-1 flex-wrap">
        <span className="text-sm text-muted-foreground">{alert.alert_name}</span>
        <span className="text-xs text-muted-foreground bg-muted rounded px-1.5 py-0.5">
          {alert.exchange}
        </span>
        <span className="text-xs text-muted-foreground">
          {formatTimestamp(alert.received_at)}
        </span>
      </div>

      {/* OHLCV strip */}
      <div className="mt-3">
        <OhlcvStrip
          open={alert.price_open}
          high={alert.price_high}
          low={alert.price_low}
          close={alert.price_close}
          volume={alert.volume}
        />
      </div>

      {/* Price at alert */}
      {alert.price_at_alert != null && (
        <div className="mt-2 rounded-md bg-blue-50 border border-blue-100 px-3 py-1.5 flex items-center justify-between">
          <span className="text-xs font-medium text-blue-700">Price at Alert</span>
          <span className="text-sm font-bold text-blue-900">
            {formatPrice(alert.price_at_alert)}
          </span>
        </div>
      )}

      {/* Action buttons */}
      {showActions && (
        <div className="flex gap-2 pt-3 border-t mt-3">
          <Button
            className="flex-1 rounded-full"
            onClick={() => onApprove?.(alert.id)}
          >
            Approve
          </Button>
          <Button
            variant="outline"
            className="flex-1 rounded-full border-destructive text-destructive hover:bg-destructive/10"
            onClick={() => onDeny?.(alert.id)}
          >
            Deny
          </Button>
        </div>
      )}
    </div>
  );
}
