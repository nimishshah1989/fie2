"use client";

import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Line, ComposedChart, Legend,
} from "recharts";
import { usePmsNav } from "@/hooks/use-pms-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface PmsNavChartProps {
  portfolioId: number;
}

const PERIODS = ["1M", "3M", "6M", "1Y", "3Y", "ALL"] as const;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
}

export function PmsNavChart({ portfolioId }: PmsNavChartProps) {
  const [period, setPeriod] = useState<string>("ALL");
  const { navHistory } = usePmsNav(portfolioId, period === "ALL" ? "all" : period);

  if (!navHistory || navHistory.length === 0) {
    return <Skeleton className="h-80 rounded-xl" />;
  }

  // Use TWR unit_nav for chart (adjusts for capital flows)
  const hasUnitNav = navHistory.some((d) => d.unit_nav != null);
  const hasBenchmark = navHistory.some((d) => d.benchmark_nav != null);

  const chartData = navHistory.map((d) => ({
    date: d.date,
    portfolio: hasUnitNav && d.unit_nav != null ? d.unit_nav : d.nav,
    benchmark: d.benchmark_nav ?? undefined,
  }));

  // Compute domain for Y-axis — include both portfolio and benchmark values
  const allValues = chartData.flatMap((d) => {
    const vals = [d.portfolio];
    if (d.benchmark != null) vals.push(d.benchmark);
    return vals;
  });
  const minVal = Math.min(...allValues);
  const maxVal = Math.max(...allValues);
  const padding = (maxVal - minVal) * 0.05;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">
          {hasUnitNav ? "TWR Performance (Base 100)" : "NAV History"}
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

      <ResponsiveContainer width="100%" height={320}>
        <ComposedChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="navGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#0d9488" stopOpacity={0.2} />
              <stop offset="95%" stopColor="#0d9488" stopOpacity={0} />
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
            tickFormatter={(v: number) =>
              hasUnitNav
                ? v.toLocaleString("en-IN", { maximumFractionDigits: 0 })
                : `₹${v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
            }
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            domain={[minVal - padding, maxVal + padding]}
            width={70}
          />
          <Tooltip
            formatter={(value: number, name: string) => {
              const label = name === "portfolio" ? "Portfolio" : "NIFTY 50";
              const formatted = hasUnitNav
                ? value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
              return [formatted, label];
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
              align="right"
              height={24}
              iconSize={10}
              formatter={(value: string) => (
                <span className="text-xs text-slate-500">
                  {value === "portfolio" ? "Portfolio" : "NIFTY 50"}
                </span>
              )}
            />
          )}
          <Area
            type="monotone"
            dataKey="portfolio"
            stroke="#0d9488"
            strokeWidth={2}
            fill="url(#navGradient)"
            dot={false}
            activeDot={{ r: 4, fill: "#0d9488" }}
            name="portfolio"
          />
          {hasBenchmark && (
            <Line
              type="monotone"
              dataKey="benchmark"
              stroke="#94a3b8"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              activeDot={{ r: 3, fill: "#94a3b8" }}
              name="benchmark"
              connectNulls
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
