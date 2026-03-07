"use client";

import { useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
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

function formatNavAxis(value: number, hasUnitNav: boolean): string {
  if (hasUnitNav) return value.toLocaleString("en-IN", { maximumFractionDigits: 0 });
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function PmsNavChart({ portfolioId }: PmsNavChartProps) {
  const [period, setPeriod] = useState<string>("ALL");
  const { navHistory } = usePmsNav(portfolioId, period === "ALL" ? "all" : period);

  if (!navHistory || navHistory.length === 0) {
    return <Skeleton className="h-80 rounded-xl" />;
  }

  // Use TWR unit_nav for chart (adjusts for capital flows)
  const hasUnitNav = navHistory.some((d) => d.unit_nav != null);
  const chartData = navHistory.map((d) => ({
    ...d,
    display_nav: hasUnitNav && d.unit_nav != null ? d.unit_nav : d.nav,
  }));

  const navValues = chartData.map((d) => d.display_nav);
  const minNav = Math.min(...navValues);
  const maxNav = Math.max(...navValues);
  const padding = (maxNav - minNav) * 0.05;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">
          {hasUnitNav ? "TWR Performance (Base 100)" : "NAV History"}
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
        <AreaChart data={chartData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
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
            tickFormatter={(v: number) => formatNavAxis(v, hasUnitNav)}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            domain={[minNav - padding, maxNav + padding]}
            width={70}
          />
          <Tooltip
            formatter={(value: number) => [
              hasUnitNav
                ? value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
              hasUnitNav ? "TWR Index" : "NAV",
            ]}
            labelFormatter={formatDate}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              fontSize: "12px",
            }}
          />
          <Area
            type="monotone"
            dataKey="display_nav"
            stroke="#0d9488"
            strokeWidth={2}
            fill="url(#navGradient)"
            dot={false}
            activeDot={{ r: 4, fill: "#0d9488" }}
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
