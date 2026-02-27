"use client";

import { useEffect, useState } from "react";
import { ImageOff, Lightbulb, Pencil, Trash2 } from "lucide-react";
import type { Alert } from "@/lib/types";
import { fetchChart } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { OhlcvStrip } from "@/components/ohlcv-strip";

interface DetailPanelProps {
  alert: Alert;
  onClose: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
}

export function DetailPanel({ alert, onClose, onEdit, onDelete }: DetailPanelProps) {
  const [chartData, setChartData] = useState<string>("");
  const [chartLoading, setChartLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setChartLoading(true);
    setChartData("");

    fetchChart(alert.id)
      .then((data) => {
        if (!cancelled) {
          setChartData(data);
          setChartLoading(false);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setChartLoading(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [alert.id]);

  const action = alert.action;
  const insights = action?.chart_analysis ?? [];

  return (
    <div className="space-y-6">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 min-w-0">
          <h2 className="text-xl font-bold">{alert.ticker}</h2>
          <span className="text-sm text-muted-foreground truncate">{alert.alert_name}</span>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {onEdit && (
            <Button variant="ghost" size="icon" onClick={onEdit} title="Edit action">
              <Pencil className="h-4 w-4" />
            </Button>
          )}
          {onDelete && (
            <Button variant="ghost" size="icon" onClick={onDelete} title="Delete alert" className="text-red-500 hover:text-red-600 hover:bg-red-50">
              <Trash2 className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>

      {/* Content: Chart + Insights (stacked in sheet) */}
      <div className="grid grid-cols-1 gap-6">
        {/* Left: Chart */}
        <div className="flex flex-col">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-3">
            Chart
          </h3>
          {chartLoading ? (
            <Skeleton className="w-full aspect-[4/3] rounded-lg" />
          ) : chartData ? (
            <img
              src={`data:image/png;base64,${chartData}`}
              alt={`Chart for ${alert.ticker}`}
              className="w-full rounded-lg border"
            />
          ) : (
            <div className="flex flex-col items-center justify-center w-full aspect-[4/3] rounded-lg border border-dashed bg-muted/30">
              <ImageOff className="h-10 w-10 text-muted-foreground/40 mb-2" />
              <span className="text-sm text-muted-foreground">No chart attached</span>
            </div>
          )}
        </div>

        {/* Right: Insights */}
        <div className="flex flex-col">
          <div className="flex items-center gap-2 mb-3">
            <Lightbulb className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Insights
            </h3>
          </div>
          {insights.length > 0 ? (
            <div className="space-y-3">
              {insights.map((insight, index) => (
                <div
                  key={index}
                  className="flex gap-3 text-sm border-l-2 border-muted-foreground/20 pl-3 py-1"
                >
                  <span className="text-muted-foreground font-semibold tabular-nums shrink-0">
                    {index + 1}.
                  </span>
                  <span className="text-foreground leading-relaxed">{insight}</span>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex items-center justify-center h-32 rounded-lg border border-dashed bg-muted/30">
              <span className="text-sm text-muted-foreground">No insights available</span>
            </div>
          )}
        </div>
      </div>

      {/* FM Notes */}
      {action?.fm_notes && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            FM Notes
          </h3>
          <div className="bg-muted/50 rounded-lg px-4 py-3 text-sm text-foreground leading-relaxed">
            {action.fm_notes}
          </div>
        </div>
      )}

      {/* Trade Parameters */}
      {action && (action.entry_price_low != null || action.entry_price_high != null || action.stop_loss != null || action.target_price != null) && (
        <div>
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            Trade Parameters
          </h3>
          <div className="grid grid-cols-2 gap-3">
            {(action.entry_price_low != null || action.entry_price_high != null) && (
              <div className="bg-blue-50 rounded-lg px-3 py-2.5">
                <div className="text-[11px] text-blue-600 font-medium uppercase tracking-wide">Entry Range</div>
                <div className="text-sm font-semibold text-blue-800 mt-0.5">
                  ₹{action.entry_price_low ?? "—"} – ₹{action.entry_price_high ?? "—"}
                </div>
              </div>
            )}
            {action.stop_loss != null && (
              <div className="bg-red-50 rounded-lg px-3 py-2.5">
                <div className="text-[11px] text-red-600 font-medium uppercase tracking-wide">Stop Loss</div>
                <div className="text-sm font-semibold text-red-800 mt-0.5">₹{action.stop_loss}</div>
              </div>
            )}
            {action.target_price != null && (
              <div className="bg-emerald-50 rounded-lg px-3 py-2.5">
                <div className="text-[11px] text-emerald-600 font-medium uppercase tracking-wide">Target Price</div>
                <div className="text-sm font-semibold text-emerald-800 mt-0.5">₹{action.target_price}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* OHLCV Strip */}
      <OhlcvStrip
        open={alert.price_open}
        high={alert.price_high}
        low={alert.price_low}
        close={alert.price_close}
        volume={alert.volume}
      />
    </div>
  );
}
