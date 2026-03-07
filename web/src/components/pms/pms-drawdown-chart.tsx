"use client";

import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, ReferenceLine,
} from "recharts";
import { usePmsNav } from "@/hooks/use-pms-detail";
import { Skeleton } from "@/components/ui/skeleton";

interface PmsDrawdownChartProps {
  portfolioId: number;
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" });
}

export function PmsDrawdownChart({ portfolioId }: PmsDrawdownChartProps) {
  const { navHistory } = usePmsNav(portfolioId, "all");

  if (!navHistory || navHistory.length < 2) {
    return <Skeleton className="h-64 rounded-xl" />;
  }

  // Compute drawdown series from NAV data
  let runningMax = 0;
  const drawdownData = navHistory.map((d) => {
    runningMax = Math.max(runningMax, d.nav);
    const dd = ((d.nav - runningMax) / runningMax) * 100;
    return { date: d.date, drawdown: Math.round(dd * 100) / 100 };
  });

  const minDD = Math.min(...drawdownData.map((d) => d.drawdown));

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-sm font-semibold text-slate-700 mb-4">Underwater Chart (Drawdown %)</h3>
      <ResponsiveContainer width="100%" height={240}>
        <AreaChart data={drawdownData} margin={{ top: 5, right: 10, left: 10, bottom: 5 }}>
          <defs>
            <linearGradient id="ddGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#ef4444" stopOpacity={0.05} />
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
            formatter={(value: number) => [`${value.toFixed(2)}%`, "Drawdown"]}
            labelFormatter={formatDate}
            contentStyle={{
              borderRadius: "8px",
              border: "1px solid #e2e8f0",
              fontSize: "12px",
            }}
          />
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
    </div>
  );
}
