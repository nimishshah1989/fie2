"use client";

import { useState, useMemo } from "react";
import {
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Line,
  ComposedChart,
  ReferenceLine,
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { PeriodToggle } from "@/components/portfolio/period-toggle";
import { useNAVHistory } from "@/hooks/use-portfolio-detail";
import type { NAVDataPoint } from "@/lib/portfolio-types";

interface PortfolioChartProps {
  portfolioId: number;
}

// Format large INR values for Y-axis: ₹8.1Cr, ₹50.7L, ₹1,200
function formatAxisValue(v: number): string {
  if (v >= 10000000) return `₹${(v / 10000000).toFixed(1)}Cr`;
  if (v >= 100000) return `₹${(v / 100000).toFixed(1)}L`;
  if (v >= 1000) return `₹${(v / 1000).toFixed(0)}K`;
  return `₹${v.toFixed(0)}`;
}

// Format INR with commas (Indian locale)
function formatINR(v: number): string {
  return `₹${v.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

// Format date for X-axis ticks
function formatDateTick(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
  } catch {
    return dateStr;
  }
}

// Format date for tooltip header
function formatDateFull(dateStr: string): string {
  try {
    const d = new Date(dateStr + "T00:00:00");
    return d.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return dateStr;
  }
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
  payload: NAVDataPoint;
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: TooltipPayloadItem[];
  label?: string;
}) {
  if (!active || !payload || !payload.length) return null;

  const dataPoint = payload[0]?.payload;
  if (!dataPoint) return null;

  const portfolioVal = dataPoint.total_value;
  const costVal = dataPoint.total_cost;
  const benchmarkVal = dataPoint.benchmark_value;
  const unrealizedPnl = dataPoint.unrealized_pnl;
  const returnPct =
    costVal > 0 ? ((portfolioVal - costVal) / costVal) * 100 : 0;

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-xl p-3 text-xs min-w-[200px]">
      <div className="font-semibold text-slate-900 mb-2 text-[13px]">
        {formatDateFull(dataPoint.date)}
      </div>

      {/* Portfolio value */}
      <div className="flex items-center justify-between gap-4 mb-1">
        <span className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="text-slate-500">Portfolio</span>
        </span>
        <span className="font-mono font-semibold text-slate-900">
          {formatINR(portfolioVal)}
        </span>
      </div>

      {/* Cost basis */}
      <div className="flex items-center justify-between gap-4 mb-1">
        <span className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <span className="text-slate-500">Cost Basis</span>
        </span>
        <span className="font-mono font-semibold text-slate-900">
          {formatINR(costVal)}
        </span>
      </div>

      {/* Benchmark */}
      {benchmarkVal != null && benchmarkVal > 0 && (
        <div className="flex items-center justify-between gap-4 mb-1">
          <span className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-slate-400" />
            <span className="text-slate-500">Benchmark</span>
          </span>
          <span className="font-mono font-semibold text-slate-900">
            {formatINR(benchmarkVal)}
          </span>
        </div>
      )}

      {/* P&L */}
      <div className="border-t border-slate-100 mt-2 pt-2">
        <div className="flex items-center justify-between gap-4">
          <span className="text-slate-500">P&L</span>
          <span
            className={`font-mono font-bold ${
              unrealizedPnl >= 0 ? "text-emerald-600" : "text-red-600"
            }`}
          >
            {unrealizedPnl >= 0 ? "+" : ""}
            {formatINR(unrealizedPnl)} ({returnPct >= 0 ? "+" : ""}
            {returnPct.toFixed(2)}%)
          </span>
        </div>
      </div>
    </div>
  );
}

export function PortfolioChart({ portfolioId }: PortfolioChartProps) {
  const [period, setPeriod] = useState("ALL");
  const { navHistory } = useNAVHistory(portfolioId, period);

  // Downsample for very large datasets (keep at most ~300 points for smooth rendering)
  const chartData = useMemo(() => {
    if (navHistory.length <= 300) return navHistory;
    const step = Math.ceil(navHistory.length / 300);
    const sampled: NAVDataPoint[] = [];
    for (let i = 0; i < navHistory.length; i += step) {
      sampled.push(navHistory[i]);
    }
    // Always include last data point
    if (sampled[sampled.length - 1] !== navHistory[navHistory.length - 1]) {
      sampled.push(navHistory[navHistory.length - 1]);
    }
    return sampled;
  }, [navHistory]);

  if (navHistory.length === 0) {
    return (
      <Card>
        <CardContent className="p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-foreground">
              Performance
            </h3>
            <PeriodToggle selected={period} onChange={setPeriod} />
          </div>
          <div className="h-64 flex items-center justify-center text-sm text-muted-foreground">
            No NAV data yet. Compute NAV to see the chart.
          </div>
        </CardContent>
      </Card>
    );
  }

  const hasBenchmark = navHistory.some((d) => d.benchmark_value != null && d.benchmark_value > 0);

  // Calculate summary stats
  const firstPoint = navHistory[0];
  const lastPoint = navHistory[navHistory.length - 1];
  const totalReturn =
    firstPoint.total_value > 0
      ? ((lastPoint.total_value - firstPoint.total_value) /
          firstPoint.total_value) *
        100
      : 0;

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Performance
            </h3>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-lg font-bold text-slate-900">
                {formatINR(lastPoint.total_value)}
              </span>
              <span
                className={`text-sm font-semibold ${
                  totalReturn >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {totalReturn >= 0 ? "+" : ""}
                {totalReturn.toFixed(2)}%
              </span>
            </div>
          </div>
          <PeriodToggle selected={period} onChange={setPeriod} />
        </div>

        <ResponsiveContainer width="100%" height={340}>
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 10, left: 0, bottom: 5 }}
          >
            <defs>
              <linearGradient
                id="portfolioGradient"
                x1="0"
                y1="0"
                x2="0"
                y2="1"
              >
                <stop offset="0%" stopColor="#059669" stopOpacity={0.15} />
                <stop offset="100%" stopColor="#059669" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#f1f5f9"
              vertical={false}
            />
            <XAxis
              dataKey="date"
              tickFormatter={formatDateTick}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={{ stroke: "#e2e8f0" }}
              interval="preserveStartEnd"
              minTickGap={60}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickFormatter={formatAxisValue}
              tickLine={false}
              axisLine={false}
              width={65}
              domain={["auto", "auto"]}
            />
            <Tooltip
              content={<CustomTooltip />}
              cursor={{
                stroke: "#94a3b8",
                strokeWidth: 1,
                strokeDasharray: "4 4",
              }}
            />

            {/* Cost basis line (dashed amber) */}
            <Line
              type="monotone"
              dataKey="total_cost"
              stroke="#d97706"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              dot={false}
              name="total_cost"
              activeDot={false}
            />

            {/* Benchmark line (dashed grey) */}
            {hasBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmark_value"
                stroke="#94a3b8"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
                name="benchmark_value"
                activeDot={false}
              />
            )}

            {/* Portfolio line + area fill */}
            <Area
              type="monotone"
              dataKey="total_value"
              stroke="#059669"
              strokeWidth={2}
              fill="url(#portfolioGradient)"
              name="total_value"
              activeDot={{
                r: 4,
                stroke: "#059669",
                strokeWidth: 2,
                fill: "#fff",
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>

        {/* Legend */}
        <div className="flex items-center gap-5 mt-2 text-xs text-slate-500">
          <span className="flex items-center gap-1.5">
            <div className="w-4 h-0.5 bg-emerald-600 rounded" />
            Portfolio Value
          </span>
          <span className="flex items-center gap-1.5">
            <div
              className="w-4"
              style={{
                borderTop: "2px dashed #d97706",
                height: 0,
              }}
            />
            Cost Basis
          </span>
          {hasBenchmark && (
            <span className="flex items-center gap-1.5">
              <div
                className="w-4"
                style={{
                  borderTop: "2px dashed #94a3b8",
                  height: 0,
                }}
              />
              NIFTY 50 (Normalized)
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
