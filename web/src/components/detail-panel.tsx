"use client";

import { useEffect, useState } from "react";
import { X, ImageOff, Lightbulb } from "lucide-react";
import type { Alert } from "@/lib/types";
import { fetchChart } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { OhlcvStrip } from "@/components/ohlcv-strip";

interface DetailPanelProps {
  alert: Alert;
  onClose: () => void;
}

export function DetailPanel({ alert, onClose }: DetailPanelProps) {
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
    <div className="bg-card rounded-xl border shadow-lg p-6 mb-6 animate-in fade-in slide-in-from-top-2 duration-300">
      {/* Header row */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <h2 className="text-xl font-bold">{alert.ticker}</h2>
          <span className="text-sm text-muted-foreground">{alert.alert_name}</span>
        </div>
        <Button variant="ghost" size="icon" onClick={onClose} className="shrink-0">
          <X className="h-5 w-5" />
        </Button>
      </div>

      {/* Two-column content: Chart + Insights */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
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
        <div className="mb-6">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wide mb-2">
            FM Notes
          </h3>
          <div className="bg-muted/50 rounded-lg px-4 py-3 text-sm text-foreground leading-relaxed">
            {action.fm_notes}
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
