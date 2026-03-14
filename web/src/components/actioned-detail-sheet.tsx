"use client";

import type { ActionedAlert } from "@/lib/types";
import { cn, formatPrice, formatPct, formatTimestamp } from "@/lib/utils";
import { Sheet, SheetContent } from "@/components/ui/sheet";

interface ActionedDetailSheetProps {
  alert: ActionedAlert | null;
  onClose: () => void;
}

const SIGNAL_COLORS: Record<string, string> = {
  BULLISH: "bg-emerald-50 text-emerald-700 border-emerald-200",
  BEARISH: "bg-red-50 text-red-700 border-red-200",
  NEUTRAL: "bg-slate-50 text-slate-600 border-slate-200",
};

function TradeParamBlock({ label, value, colorClass }: {
  label: string;
  value: string;
  colorClass: string;
}) {
  return (
    <div className={cn("rounded-lg px-3 py-2.5", colorClass)}>
      <div className="text-[11px] font-medium uppercase tracking-wide opacity-70">{label}</div>
      <div className="text-sm font-semibold font-mono mt-0.5">{value}</div>
    </div>
  );
}

export function ActionedDetailSheet({ alert, onClose }: ActionedDetailSheetProps) {
  if (!alert) return null;

  const returnPct = alert.is_closed ? alert.closed_pnl_pct : alert.return_pct;
  const isPositive = (returnPct ?? 0) >= 0;
  const signalClass = SIGNAL_COLORS[alert.signal_direction] ?? SIGNAL_COLORS.NEUTRAL;

  return (
    <Sheet open={alert !== null} onOpenChange={(open) => { if (!open) onClose(); }}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto p-0">
        <div className="p-6 space-y-6">
          {/* Header */}
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h2 className="text-xl font-bold text-slate-800">{alert.ticker}</h2>
              <span className={cn("inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5 border", signalClass)}>
                {alert.signal_direction}
              </span>
              {alert.priority && (
                <span className={cn(
                  "text-xs font-medium rounded-full px-2.5 py-0.5",
                  alert.priority === "IMMEDIATELY" ? "bg-orange-100 text-orange-700" :
                  alert.priority === "WITHIN_A_WEEK" ? "bg-blue-100 text-blue-700" :
                  "bg-purple-100 text-purple-700"
                )}>
                  {alert.priority === "IMMEDIATELY" ? "Immediately" :
                   alert.priority === "WITHIN_A_WEEK" ? "Within a Week" : "Within a Month"}
                </span>
              )}
              {alert.is_closed && (
                <span className="bg-slate-100 text-slate-600 text-xs font-medium rounded-full px-2.5 py-0.5">
                  CLOSED
                </span>
              )}
            </div>
            <p className="text-sm text-slate-500 mt-1">
              {alert.alert_name} &middot; {alert.interval} &middot; {formatTimestamp(alert.received_at)}
            </p>
          </div>

          {/* Current Price + P&L */}
          <div className="bg-slate-50 rounded-xl border border-slate-200 p-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wide">Current Price</div>
                <div className="text-lg font-bold font-mono text-slate-800 mt-1">
                  {alert.current_price != null ? `₹${formatPrice(alert.current_price)}` : "---"}
                </div>
              </div>
              <div>
                <div className="text-xs text-slate-400 uppercase tracking-wide">
                  {alert.is_closed ? "Realized P&L" : "Unrealized P&L"}
                </div>
                <div className={cn(
                  "text-lg font-bold font-mono mt-1",
                  isPositive ? "text-emerald-600" : "text-red-600"
                )}>
                  {returnPct != null ? formatPct(returnPct) : "---"}
                </div>
              </div>
            </div>
            {alert.days_since != null && (
              <p className="text-xs text-slate-400 mt-2">
                {alert.days_since === 0 ? "Actioned today" : `${alert.days_since} days since action`}
              </p>
            )}
          </div>

          {/* Trade Parameters */}
          {(alert.entry_price_low != null || alert.stop_loss != null || alert.target_price != null) && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Trade Parameters
              </h3>
              <div className="grid grid-cols-2 gap-3">
                {(alert.entry_price_low != null || alert.entry_price_high != null) && (
                  <TradeParamBlock
                    label="Entry Range"
                    value={`₹${formatPrice(alert.entry_price_low)} – ₹${formatPrice(alert.entry_price_high)}`}
                    colorClass="bg-blue-50 text-blue-800"
                  />
                )}
                {alert.stop_loss != null && (
                  <TradeParamBlock
                    label="Stop Loss"
                    value={`₹${formatPrice(alert.stop_loss)}`}
                    colorClass="bg-red-50 text-red-800"
                  />
                )}
                {alert.target_price != null && (
                  <TradeParamBlock
                    label="Target Price"
                    value={`₹${formatPrice(alert.target_price)}`}
                    colorClass="bg-emerald-50 text-emerald-800"
                  />
                )}
              </div>
            </div>
          )}

          {/* Threshold Status */}
          <div>
            <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Threshold Status
            </h3>
            <div className="flex gap-3">
              {[
                { label: "Entry Hit", hit: alert.entry_hit },
                { label: "Target Hit", hit: alert.target_hit },
                { label: "SL Hit", hit: alert.sl_hit },
              ].map((item) => (
                <div
                  key={item.label}
                  className={cn(
                    "flex-1 rounded-lg border px-3 py-2 text-center text-xs font-medium",
                    item.hit
                      ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                      : "bg-slate-50 border-slate-200 text-slate-400"
                  )}
                >
                  {item.label} {item.hit ? "\u2713" : "\u2717"}
                </div>
              ))}
            </div>
          </div>

          {/* FM Notes */}
          {alert.fm_notes && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                FM Commentary
              </h3>
              <div className="bg-slate-50 rounded-lg border border-slate-200 px-4 py-3 text-sm text-slate-700 leading-relaxed">
                {alert.fm_notes}
              </div>
            </div>
          )}

          {/* Chart Analysis */}
          {alert.chart_analysis && alert.chart_analysis.length > 0 && (
            <div>
              <h3 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                AI Chart Insights
              </h3>
              <div className="space-y-2">
                {alert.chart_analysis.map((insight, index) => (
                  <div key={index} className="flex gap-3 text-sm border-l-2 border-slate-200 pl-3 py-1">
                    <span className="text-slate-400 font-semibold tabular-nums shrink-0">{index + 1}.</span>
                    <span className="text-slate-700 leading-relaxed">{insight}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Closed At */}
          {alert.is_closed && alert.closed_at && (
            <p className="text-xs text-slate-400">
              Closed on {new Date(alert.closed_at).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
            </p>
          )}
        </div>
      </SheetContent>
    </Sheet>
  );
}
