"use client";

import type { Alert } from "@/lib/types";
import { cn, formatPrice, formatTimestamp } from "@/lib/utils";
import { OhlcvStrip } from "@/components/ohlcv-strip";
import { Button } from "@/components/ui/button";
import { CheckCircle2, XCircle, Eye } from "lucide-react";

interface AlertCardCompactProps {
  alert: Alert;
  onApprove: (id: number) => void;
  onDeny: (id: number) => void;
  onWatch: (id: number) => void;
}

export function AlertCardCompact({
  alert,
  onApprove,
  onDeny,
  onWatch,
}: AlertCardCompactProps) {
  return (
    <div
      className="rounded-xl border bg-card shadow-sm hover:shadow-md transition-shadow p-4 flex flex-col gap-3 overflow-hidden"
    >
      {/* Header: Ticker + Exchange + Interval */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="font-bold text-base text-foreground">
            {alert.ticker}
          </span>
          <span className="text-[10px] font-medium text-muted-foreground bg-muted rounded px-1.5 py-0.5 uppercase">
            {alert.exchange}
          </span>
        </div>
        <span className="text-xs font-medium text-muted-foreground bg-muted rounded-md px-2 py-0.5">
          {alert.interval}
        </span>
      </div>

      {/* Time */}
      <div className="text-xs text-muted-foreground">
        {formatTimestamp(alert.received_at)}
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
          <span className="text-xs font-medium text-blue-700">Close</span>
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
          className="flex-1 border-amber-300 text-amber-600 hover:bg-amber-50 hover:text-amber-700"
          onClick={() => onWatch(alert.id)}
        >
          <Eye className="h-3.5 w-3.5" />
          Watch
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
