"use client";

import type { ActionedAlert } from "@/lib/types";
import { cn, formatPrice, formatPct } from "@/lib/utils";

interface ActionedCardProps {
  alert: ActionedAlert;
  onClick?: () => void;
}

const SIGNAL_BORDER: Record<string, string> = {
  BULLISH: "border-l-emerald-500",
  BEARISH: "border-l-red-500",
  NEUTRAL: "border-l-slate-300",
};

function ActionCallBadge({ actionCall }: { actionCall: string }) {
  const upper = actionCall.toUpperCase();
  const isBuy = upper === "BUY" || upper === "ACCUMULATE";
  const isSell = upper === "SELL" || upper === "REDUCE";
  return (
    <span
      className={cn(
        "inline-flex items-center text-xs font-semibold rounded-full px-2.5 py-0.5",
        isBuy && "bg-emerald-100 text-emerald-700",
        isSell && "bg-red-100 text-red-700",
        !isBuy && !isSell && "bg-slate-100 text-slate-700"
      )}
    >
      {upper}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const config: Record<string, string> = {
    IMMEDIATELY: "bg-orange-100 text-orange-700",
    WITHIN_A_WEEK: "bg-blue-100 text-blue-700",
    WITHIN_A_MONTH: "bg-purple-100 text-purple-700",
  };
  const labels: Record<string, string> = {
    IMMEDIATELY: "Immediately",
    WITHIN_A_WEEK: "Within a Week",
    WITHIN_A_MONTH: "Within a Month",
  };
  return (
    <span className={cn("text-xs font-medium rounded-full px-2.5 py-0.5", config[priority] ?? "bg-slate-100 text-slate-600")}>
      {labels[priority] ?? priority}
    </span>
  );
}

function ThresholdPill({ label, hit }: { label: string; hit: boolean }) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 text-[10px] font-medium rounded-full px-2 py-0.5",
        hit ? "bg-emerald-50 text-emerald-700" : "bg-slate-50 text-slate-400"
      )}
    >
      {label} {hit ? "\u2713" : "\u2717"}
    </span>
  );
}

export function ActionedCard({ alert, onClick }: ActionedCardProps) {
  const borderColor = SIGNAL_BORDER[alert.signal_direction] ?? SIGNAL_BORDER.NEUTRAL;
  const returnPct = alert.is_closed ? alert.closed_pnl_pct : alert.return_pct;
  const isPositive = (returnPct ?? 0) >= 0;

  const daysSinceLabel = alert.days_since != null
    ? alert.days_since === 0 ? "today" : `${alert.days_since}d ago`
    : "";

  return (
    <div
      onClick={onClick}
      className={cn(
        "bg-white rounded-xl border border-slate-200 border-l-4 p-4 cursor-pointer",
        "hover:shadow-md transition-shadow",
        borderColor
      )}
    >
      {/* Row 1: Ticker + Action call + Priority */}
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-base font-semibold text-slate-800">{alert.ticker}</span>
        <span className="text-xs text-slate-400">{alert.interval}</span>
        {alert.action_call && <ActionCallBadge actionCall={alert.action_call} />}
        {alert.priority && <PriorityBadge priority={alert.priority} />}
        {alert.is_closed && (
          <span className="bg-slate-100 text-slate-600 text-xs font-medium rounded-full px-2.5 py-0.5">
            CLOSED
          </span>
        )}
      </div>

      {/* Row 2: Signal + days since */}
      <div className="flex items-center gap-2 mt-1.5 text-xs">
        <span className={cn(
          "font-medium",
          alert.signal_direction === "BULLISH" ? "text-emerald-600" :
          alert.signal_direction === "BEARISH" ? "text-red-600" : "text-slate-500"
        )}>
          Signal: {alert.signal_direction}
        </span>
        {daysSinceLabel && (
          <>
            <span className="text-slate-300">|</span>
            <span className="text-slate-400">{daysSinceLabel}</span>
          </>
        )}
      </div>

      {/* Row 3: Trade parameters */}
      {(alert.entry_price_low != null || alert.stop_loss != null || alert.target_price != null) && (
        <div className="flex gap-2 mt-3">
          {(alert.entry_price_low != null || alert.entry_price_high != null) && (
            <div className="bg-slate-50 rounded-lg px-2.5 py-1.5 flex-1 min-w-0">
              <div className="text-[10px] text-slate-400 uppercase tracking-wide">Entry</div>
              <div className="text-xs font-mono font-medium text-slate-700 mt-0.5">
                {alert.entry_price_low != null ? `₹${formatPrice(alert.entry_price_low)}` : "—"}
                {alert.entry_price_high != null ? `–${formatPrice(alert.entry_price_high)}` : ""}
              </div>
            </div>
          )}
          {alert.stop_loss != null && (
            <div className="bg-red-50 rounded-lg px-2.5 py-1.5 flex-1 min-w-0">
              <div className="text-[10px] text-red-400 uppercase tracking-wide">SL</div>
              <div className="text-xs font-mono font-medium text-red-600 mt-0.5">
                ₹{formatPrice(alert.stop_loss)}
              </div>
            </div>
          )}
          {alert.target_price != null && (
            <div className="bg-emerald-50 rounded-lg px-2.5 py-1.5 flex-1 min-w-0">
              <div className="text-[10px] text-emerald-400 uppercase tracking-wide">TP</div>
              <div className="text-xs font-mono font-medium text-emerald-600 mt-0.5">
                ₹{formatPrice(alert.target_price)}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Row 4: Current price + P&L */}
      <div className="flex items-center justify-between mt-3">
        {alert.current_price != null && (
          <div className="text-sm">
            <span className="text-slate-500 text-xs">Current: </span>
            <span className="font-mono font-semibold text-slate-800">₹{formatPrice(alert.current_price)}</span>
          </div>
        )}
        {returnPct != null && (
          <div className={cn("text-sm font-mono font-semibold", isPositive ? "text-emerald-600" : "text-red-600")}>
            {formatPct(returnPct)}
          </div>
        )}
      </div>

      {/* Row 5: Threshold pills */}
      <div className="flex items-center gap-1.5 mt-2.5">
        <ThresholdPill label="Entry Hit" hit={alert.entry_hit} />
        <ThresholdPill label="Target Hit" hit={alert.target_hit} />
        <ThresholdPill label="SL Hit" hit={alert.sl_hit} />
      </div>

      {/* Row 6: FM Notes preview */}
      {alert.fm_notes && (
        <p className="text-xs text-slate-400 line-clamp-2 leading-relaxed mt-2">
          {alert.fm_notes}
        </p>
      )}
    </div>
  );
}
