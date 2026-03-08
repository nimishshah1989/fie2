"use client";

import { useState } from "react";
import {
  XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Line, ComposedChart, Legend, Bar,
  Area,
} from "recharts";
import { usePmsNav } from "@/hooks/use-pms-detail";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";

interface PmsNavChartProps {
  portfolioId: number;
}

const PERIODS = ["1M", "3M", "6M", "1Y", "2Y", "3Y", "ALL"] as const;

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
}

function formatCashPct(value: number): string {
  return `${value.toFixed(1)}%`;
}

export function PmsNavChart({ portfolioId }: PmsNavChartProps) {
  const [period, setPeriod] = useState<string>("ALL");
  const { navHistory } = usePmsNav(portfolioId, period === "ALL" ? "all" : period);

  if (!navHistory || navHistory.length === 0) {
    return <Skeleton className="h-80 rounded-xl" />;
  }

  const hasUnitNav = navHistory.some((d) => d.unit_nav != null);
  const hasBenchmark = navHistory.some((d) => d.benchmark_nav != null);
  const hasCash = navHistory.some(
    (d) => (d.cash_equivalent != null && d.cash_equivalent > 0) ||
           (d.bank_balance != null && d.bank_balance > 0) ||
           (d.liquidity_pct != null && d.liquidity_pct > 0)
  );

  // Get first-day values for rebasing both lines to 100
  const firstPortfolio = hasUnitNav && navHistory[0].unit_nav != null
    ? navHistory[0].unit_nav : navHistory[0].nav;
  const firstBenchmark = navHistory.find((d) => d.benchmark_nav != null)?.benchmark_nav ?? null;

  const chartData = navHistory.map((d) => {
    const rawPort = hasUnitNav && d.unit_nav != null ? d.unit_nav : d.nav;
    const rebasedPort = (rawPort / firstPortfolio) * 100;
    const rebasedBench = d.benchmark_nav != null && firstBenchmark != null
      ? (d.benchmark_nav / firstBenchmark) * 100
      : undefined;
    // Cash as % of NAV — use liquidity_pct if available, else compute from raw values
    let cashPct: number | undefined;
    if (hasCash) {
      if (d.liquidity_pct != null) {
        cashPct = Math.max(0, d.liquidity_pct);
      } else {
        const cashAbs = (d.cash_equivalent || 0) + (d.bank_balance || 0);
        cashPct = d.nav > 0 ? Math.max(0, (cashAbs / d.nav) * 100) : 0;
      }
    }
    return {
      date: d.date,
      portfolio: Math.round(rebasedPort * 100) / 100,
      benchmark: rebasedBench != null ? Math.round(rebasedBench * 100) / 100 : undefined,
      cash: cashPct,
    };
  });

  // Y-axis domain for portfolio/benchmark (rebased)
  const navValues = chartData.flatMap((d) => {
    const vals = [d.portfolio];
    if (d.benchmark != null) vals.push(d.benchmark);
    return vals;
  });
  const minNav = Math.min(...navValues);
  const maxNav = Math.max(...navValues);
  const navPadding = (maxNav - minNav) * 0.05;

  // Y-axis domain for cash % (secondary)
  const cashValues = chartData.map((d) => d.cash || 0).filter((v) => v > 0);
  const maxCashPct = cashValues.length > 0 ? Math.min(Math.max(...cashValues) * 1.2, 100) : 50;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-slate-700">
          Relative Performance (Base 100)
          {hasBenchmark && <span className="text-slate-400 font-normal"> vs NIFTY 50</span>}
          {hasCash && <span className="text-slate-400 font-normal"> | Cash % of NAV</span>}
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

      <ResponsiveContainer width="100%" height={360}>
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
          {/* Primary Y-axis: rebased index */}
          <YAxis
            yAxisId="nav"
            tickFormatter={(v: number) => v.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            tickLine={false}
            axisLine={false}
            domain={[minNav - navPadding, maxNav + navPadding]}
            width={55}
          />
          {/* Secondary Y-axis: Cash as % of NAV */}
          {hasCash && (
            <YAxis
              yAxisId="cash"
              orientation="right"
              tickFormatter={formatCashPct}
              tick={{ fontSize: 10, fill: "#94a3b8" }}
              tickLine={false}
              axisLine={false}
              domain={[0, maxCashPct]}
              width={50}
            />
          )}
          <Tooltip
            formatter={(value: number, name: string) => {
              if (name === "cash") return [`${value.toFixed(1)}% of NAV`, "Cash Position"];
              const label = name === "portfolio" ? "Portfolio" : "NIFTY 50";
              const pctChange = value - 100;
              const sign = pctChange >= 0 ? "+" : "";
              const formatted = `${value.toFixed(2)} (${sign}${pctChange.toFixed(2)}%)`;
              return [formatted, label];
            }}
            labelFormatter={formatDate}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              fontSize: "12px",
            }}
          />
          <Legend
            verticalAlign="top"
            align="center"
            height={24}
            iconSize={10}
            formatter={(value: string) => {
              const labels: Record<string, string> = {
                portfolio: "Portfolio",
                benchmark: "NIFTY 50",
                cash: "Cash % of NAV",
              };
              return (
                <span className="text-xs text-slate-500">{labels[value] || value}</span>
              );
            }}
          />
          {/* Cash bars (behind lines) */}
          {hasCash && (
            <Bar
              yAxisId="cash"
              dataKey="cash"
              fill="#fbbf24"
              opacity={0.25}
              name="cash"
              barSize={2}
            />
          )}
          {/* Portfolio area */}
          <Area
            yAxisId="nav"
            type="monotone"
            dataKey="portfolio"
            stroke="#0d9488"
            strokeWidth={2}
            fill="url(#navGradient)"
            dot={false}
            activeDot={{ r: 4, fill: "#0d9488" }}
            name="portfolio"
          />
          {/* NIFTY 50 benchmark line */}
          {hasBenchmark && (
            <Line
              yAxisId="nav"
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

      {hasCash && (
        <p className="text-[11px] text-slate-400 mt-2 text-center italic">
          Amber bars = Cash (liquid funds + bank balance) as % of total NAV on each day.
          Uninvested capital held as a tactical risk management position — &quot;Cash is a position.&quot;
        </p>
      )}
    </div>
  );
}
