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
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { PeriodToggle } from "@/components/portfolio/period-toggle";
import { useNAVHistory } from "@/hooks/use-portfolio-detail";
import type { NAVDataPoint } from "@/lib/portfolio-types";

interface PortfolioChartProps {
  portfolioId: number;
}

// Percentage-based chart data point
interface PctDataPoint {
  date: string;
  portfolio_pct: number;
  cost_pct: number;
  benchmark_pct: number | null;
  // Keep raw values for tooltip
  raw_portfolio: number;
  raw_cost: number;
  raw_benchmark: number | null;
  raw_pnl: number;
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

// Format INR with commas (Indian locale)
function formatINR(v: number): string {
  return `\u20B9${v.toLocaleString("en-IN", {
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  })}`;
}

interface TooltipPayloadItem {
  name: string;
  value: number;
  color: string;
  payload: PctDataPoint;
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

  const portfolioPct = dataPoint.portfolio_pct;
  const costPct = dataPoint.cost_pct;
  const benchmarkPct = dataPoint.benchmark_pct;

  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-xl p-3 text-xs min-w-[220px]">
      <div className="font-semibold text-slate-900 mb-2 text-[13px]">
        {formatDateFull(dataPoint.date)}
      </div>

      {/* Portfolio return */}
      <div className="flex items-center justify-between gap-4 mb-1">
        <span className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-emerald-500" />
          <span className="text-slate-500">Portfolio</span>
        </span>
        <span className={`font-mono font-semibold ${portfolioPct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
          {portfolioPct >= 0 ? "+" : ""}{portfolioPct.toFixed(2)}%
        </span>
      </div>

      {/* Cost basis return */}
      <div className="flex items-center justify-between gap-4 mb-1">
        <span className="flex items-center gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-amber-400" />
          <span className="text-slate-500">Cost Basis</span>
        </span>
        <span className="font-mono font-semibold text-slate-700">
          {costPct >= 0 ? "+" : ""}{costPct.toFixed(2)}%
        </span>
      </div>

      {/* Benchmark return */}
      {benchmarkPct != null && (
        <div className="flex items-center justify-between gap-4 mb-1">
          <span className="flex items-center gap-1.5">
            <div className="w-2.5 h-2.5 rounded-full bg-slate-400" />
            <span className="text-slate-500">NIFTY 50</span>
          </span>
          <span className={`font-mono font-semibold ${benchmarkPct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
            {benchmarkPct >= 0 ? "+" : ""}{benchmarkPct.toFixed(2)}%
          </span>
        </div>
      )}

      {/* Absolute values */}
      <div className="border-t border-slate-100 mt-2 pt-2 space-y-0.5">
        <div className="flex items-center justify-between gap-4">
          <span className="text-slate-400">Value</span>
          <span className="font-mono text-slate-600">{formatINR(dataPoint.raw_portfolio)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-slate-400">Cost</span>
          <span className="font-mono text-slate-600">{formatINR(dataPoint.raw_cost)}</span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="text-slate-400">P&L</span>
          <span className={`font-mono font-bold ${dataPoint.raw_pnl >= 0 ? "text-emerald-600" : "text-red-600"}`}>
            {dataPoint.raw_pnl >= 0 ? "+" : ""}{formatINR(dataPoint.raw_pnl)}
          </span>
        </div>
      </div>
    </div>
  );
}

export function PortfolioChart({ portfolioId }: PortfolioChartProps) {
  const [period, setPeriod] = useState("ALL");
  const { navHistory } = useNAVHistory(portfolioId, period);

  // Transform NAV data to percentage returns from first data point
  const { chartData, hasBenchmark } = useMemo(() => {
    if (navHistory.length === 0) return { chartData: [] as PctDataPoint[], hasBenchmark: false };

    const first = navHistory[0];
    const basePortfolio = first.total_value || 1;
    const baseCost = first.total_cost || 1;
    const baseBenchmark = first.benchmark_value || null;
    const hasBm = navHistory.some((d) => d.benchmark_value != null && d.benchmark_value > 0);

    // Map to percentage data
    let allPct: PctDataPoint[] = navHistory.map((d) => ({
      date: d.date,
      portfolio_pct: ((d.total_value - basePortfolio) / basePortfolio) * 100,
      cost_pct: ((d.total_cost - baseCost) / baseCost) * 100,
      benchmark_pct: hasBm && baseBenchmark && d.benchmark_value
        ? ((d.benchmark_value - baseBenchmark) / baseBenchmark) * 100
        : null,
      raw_portfolio: d.total_value,
      raw_cost: d.total_cost,
      raw_benchmark: d.benchmark_value,
      raw_pnl: d.unrealized_pnl,
    }));

    // Downsample if too many points
    if (allPct.length > 300) {
      const step = Math.ceil(allPct.length / 300);
      const sampled: PctDataPoint[] = [];
      for (let i = 0; i < allPct.length; i += step) {
        sampled.push(allPct[i]);
      }
      if (sampled[sampled.length - 1] !== allPct[allPct.length - 1]) {
        sampled.push(allPct[allPct.length - 1]);
      }
      allPct = sampled;
    }

    return { chartData: allPct, hasBenchmark: hasBm };
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

  // Calculate summary stats
  const lastPoint = chartData[chartData.length - 1];
  const totalReturnPct = lastPoint?.portfolio_pct ?? 0;
  const benchmarkReturnPct = lastPoint?.benchmark_pct;

  return (
    <Card>
      <CardContent className="p-6">
        <div className="flex items-center justify-between mb-1">
          <div>
            <h3 className="text-sm font-semibold text-foreground">
              Performance (% Returns)
            </h3>
            <div className="flex items-center gap-3 mt-0.5">
              <span className="text-lg font-bold text-slate-900">
                {formatINR(lastPoint.raw_portfolio)}
              </span>
              <span
                className={`text-sm font-semibold ${
                  totalReturnPct >= 0 ? "text-emerald-600" : "text-red-600"
                }`}
              >
                {totalReturnPct >= 0 ? "+" : ""}
                {totalReturnPct.toFixed(2)}%
              </span>
              {benchmarkReturnPct != null && (
                <span className="text-xs text-slate-400">
                  vs NIFTY {benchmarkReturnPct >= 0 ? "+" : ""}{benchmarkReturnPct.toFixed(2)}%
                </span>
              )}
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
              tickFormatter={(v: number) => `${v >= 0 ? "+" : ""}${v.toFixed(0)}%`}
              tickLine={false}
              axisLine={false}
              width={55}
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
              dataKey="cost_pct"
              stroke="#d97706"
              strokeDasharray="6 3"
              strokeWidth={1.5}
              dot={false}
              name="cost_pct"
              activeDot={false}
            />

            {/* Benchmark line (dashed grey) */}
            {hasBenchmark && (
              <Line
                type="monotone"
                dataKey="benchmark_pct"
                stroke="#94a3b8"
                strokeDasharray="4 4"
                strokeWidth={1.5}
                dot={false}
                name="benchmark_pct"
                activeDot={false}
              />
            )}

            {/* Portfolio line + area fill */}
            <Area
              type="monotone"
              dataKey="portfolio_pct"
              stroke="#059669"
              strokeWidth={2}
              fill="url(#portfolioGradient)"
              name="portfolio_pct"
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
            Portfolio Return
          </span>
          <span className="flex items-center gap-1.5">
            <div
              className="w-4"
              style={{
                borderTop: "2px dashed #d97706",
                height: 0,
              }}
            />
            Cost Basis Change
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
              NIFTY 50 Return
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
