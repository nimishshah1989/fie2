"use client";

import type { Alert } from "@/lib/types";
import { cn, formatTimestamp } from "@/lib/utils";
import { SignalChip } from "@/components/signal-chip";
import { PriorityChip } from "@/components/priority-chip";
import { Badge } from "@/components/ui/badge";

interface ApprovedCardProps {
  alert: Alert;
  onClick: () => void;
  isSelected?: boolean;
}

const priorityBorderMap: Record<string, string> = {
  IMMEDIATELY: "border-t-orange-500",
  WITHIN_A_WEEK: "border-t-blue-500",
  WITHIN_A_MONTH: "border-t-purple-500",
};

function ActionCallBadge({ actionCall }: { actionCall: string }) {
  const upper = actionCall.toUpperCase();
  const isBuy = upper === "BUY" || upper === "ACCUMULATE";
  const isSell = upper === "SELL" || upper === "REDUCE";

  return (
    <span
      className={cn(
        "inline-flex items-center text-xs font-semibold rounded-full px-2.5 py-0.5",
        isBuy && "bg-emerald-100 text-emerald-800",
        isSell && "bg-red-100 text-red-800",
        !isBuy && !isSell && "bg-slate-100 text-slate-700"
      )}
    >
      {upper}
    </span>
  );
}

export function ApprovedCard({ alert, onClick, isSelected }: ApprovedCardProps) {
  const action = alert.action!;
  const priority = action.priority;
  const borderClass = priority ? priorityBorderMap[priority] ?? "" : "";
  const hasTradeParams =
    action.entry_price_low != null ||
    action.entry_price_high != null ||
    action.stop_loss != null ||
    action.target_price != null;

  return (
    <div
      onClick={onClick}
      className={cn(
        "rounded-xl border bg-card shadow-sm hover:shadow-md transition-all cursor-pointer p-4 border-t-4",
        borderClass,
        !borderClass && "border-t-transparent",
        isSelected && "ring-2 ring-blue-500 shadow-md"
      )}
    >
      {/* Header: Ticker + Signal + Interval */}
      <div className="flex items-center gap-2 mb-1">
        <span className="font-bold text-base">{alert.ticker}</span>
        <SignalChip signal={alert.signal_direction} />
        <span className="text-xs text-muted-foreground ml-auto">
          {alert.interval}
        </span>
      </div>

      {/* Alert name + timestamp */}
      <div className="mb-3">
        <div className="text-sm text-foreground truncate">{alert.alert_name}</div>
        <div className="text-xs text-muted-foreground">
          {formatTimestamp(alert.received_at)}
        </div>
      </div>

      {/* FM Action Strip */}
      <div className="flex flex-wrap items-center gap-2 mb-3">
        {action.action_call && (
          <ActionCallBadge actionCall={action.action_call} />
        )}
        <PriorityChip priority={action.priority} />
        {action.has_chart && (
          <Badge variant="secondary" className="text-xs gap-1">
            <span>📎</span> Chart
          </Badge>
        )}
        {action.chart_analysis && action.chart_analysis.length > 0 && (
          <Badge variant="secondary" className="text-xs">
            {action.chart_analysis.length} insight{action.chart_analysis.length !== 1 ? "s" : ""}
          </Badge>
        )}
      </div>

      {/* Trade Parameters Strip */}
      {hasTradeParams && (
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground mb-2">
          {(action.entry_price_low != null || action.entry_price_high != null) && (
            <span>
              Entry:{" "}
              <span className="font-medium text-foreground">
                {action.entry_price_low != null ? `₹${action.entry_price_low}` : "?"}
                –
                {action.entry_price_high != null ? `₹${action.entry_price_high}` : "?"}
              </span>
            </span>
          )}
          {action.stop_loss != null && (
            <span>
              SL: <span className="font-medium text-red-600">₹{action.stop_loss}</span>
            </span>
          )}
          {action.target_price != null && (
            <span>
              TP: <span className="font-medium text-emerald-600">₹{action.target_price}</span>
            </span>
          )}
        </div>
      )}

      {/* FM Notes preview */}
      {action.fm_notes && (
        <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">
          {action.fm_notes.length > 80
            ? action.fm_notes.slice(0, 80) + "..."
            : action.fm_notes}
        </p>
      )}
    </div>
  );
}
