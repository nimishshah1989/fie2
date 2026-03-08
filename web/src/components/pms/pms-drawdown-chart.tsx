"use client";

import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine, Legend,
} from "recharts";
import { usePmsNav } from "@/hooks/use-pms-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface PmsDrawdownChartProps {
  portfolioId: number;
}

const PERIODS = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "ALL"] as const;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
}

export function PmsDrawdownChart({ portfolioId }: PmsDrawdownChartProps) {
  const [period, setPeriod] = useState<string>("ALL");
  const { navHistory } = usePmsNav(portfolioId, period === "ALL" ? "all" : period);

  if (!navHistory || navHistory.length < 2) {
    return <Skeleton className="h-64 rounded-xl" />;
  }

  // Use TWR unit_nav for drawdown computation (adjusts for capital flows)
  const hasUnitNav = navHistory.some((d) => d.unit_nav != null);
  const hasBenchmark = navHistory.some((d) => d.benchmark_nav != null);

  let portMax = 0;
  let benchMax = 0;
  const drawdownData = navHistory.map((d) => {
    const portVal = hasUnitNav && d.unit_nav != null ? d.unit_nav : d.nav;
    portMax = Math.max(portMax, portVal);
    const portDD = ((portVal - portMax) / portMax) * 100;

    let benchDD: number | undefined;
    if (hasBenchmark && d.benchmark_nav != null) {
      benchMax = Math.max(benchMax, d.benchmark_nav);
      benchDD = ((d.benchmark_nav - benchMax) / benchMax) * 100;
    }

    return {
      date: d.date,
      drawdown: Math.round(portDD * 100) / 100,
      benchmark: benchDD != null ? Math.round(benchDD * 100) / 100 : undefined,
    };
  });

  const allDDs = drawdownData.flatMap((d) => {
    const vals = [d.drawdown];
    if (d.benchmark != null) vals.push(d.benchmark);
    return vals;
  });
  const minDD = Math.min(...allDDs);

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">
          Underwater Chart (Drawdown %)
          {hasBenchmark && <span className="text-slate-400 font-normal"> vs NIFTY 50</span>}
        </h3>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <Button
              key={p}
              variant={period === p ? "default" : "ghost"}
              size="sm"
              className="text-xs h-7 px-2.5"
              onClick={() => setPeriod(p)}
            >
              {p}
            </Button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={drawdownData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
            </linearGradient>
            <linearGradient id="ddBenchGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.15} />
              <stop offset="95%" stopColor="#94a3b8" stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={{ stroke: "#e2e8f0" }}
            minTickGap={40}
          />
          <YAxis
            tickFormatter={(v: number) => `${v.toFixed(0)}%`}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            domain={[minDD * 1.1, 0]}
            width={50}
          />
          <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="3 3" />
          <Tooltip
            formatter={(value: number, name: string) => {
              const label = name === "benchmark" ? "NIFTY 50" : "Portfolio";
              return [`${value.toFixed(2)}%`, label];
            }}
            labelFormatter={formatDate}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              fontSize: "12px",
            }}
          />
          {hasBenchmark && (
            <Legend
              verticalAlign="top"
              align="center"
              height={24}
              iconSize={10}
              formatter={(value: string) => {
                const labels: Record<string, string> = {
                  drawdown: "Portfolio",
                  benchmark: "NIFTY 50",
                };
                return (
                  <span className="text-xs text-slate-500">{labels[value] || value}</span>
                );
              }}
            />
          )}
          {/* Benchmark drawdown behind portfolio */}
          {hasBenchmark && (
            <Area
              type="monotone"
              dataKey="benchmark"
              stroke="#94a3b8"
              strokeWidth={1}
              strokeDasharray="4 3"
              fill="url(#ddBenchGradient)"
              dot={false}
              connectNulls
            />
          )}
          {/* Portfolio drawdown */}
          <Area
            type="monotone"
            dataKey="drawdown"
            stroke="#ef4444"
            strokeWidth={1.5}
            fill="url(#ddGradient)"
            dot={false}
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Explanation */}
      <div className="mt-3 pt-3 border-t border-slate-100">
        <p className="text-[11px] text-slate-500 leading-relaxed">
          <span className="font-semibold text-slate-600">What this shows:</span> The underwater chart tracks how far the portfolio has fallen from its peak at any point in time.
          A value of 0% means the portfolio is at or above its peak. A value of {drawdownData.reduce((min, d) => Math.min(min, d.drawdown), 0).toFixed(1)}% (the deepest red)
          represents the worst peak-to-trough decline in this period.
          {hasBenchmark && " The grey dashed line shows NIFTY 50 drawdowns — shallower portfolio drawdowns indicate effective risk management."}
          {hasUnitNav && " Uses TWR-adjusted values, so drawdowns reflect true investment performance excluding capital flows."}
        </p>
      </div>
    </div>
  );
}
