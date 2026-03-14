"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  ReferenceArea,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface HistoryPoint {
  date: string;
  score: number;
  zone: string;
}

interface SentimentHistoryChartProps {
  history: HistoryPoint[];
}

function formatDateLabel(dateStr: string): string {
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString("en-IN", { day: "numeric", month: "short" });
  } catch {
    return dateStr;
  }
}

function zoneLabel(score: number): string {
  if (score >= 70) return "Strong";
  if (score >= 55) return "Bullish";
  if (score >= 45) return "Neutral";
  if (score >= 30) return "Weak";
  return "Bear";
}

function zoneColor(score: number): string {
  if (score >= 70) return "#059669";
  if (score >= 55) return "#10b981";
  if (score >= 45) return "#64748b";
  if (score >= 30) return "#d97706";
  return "#dc2626";
}

export function SentimentHistoryChart({ history }: SentimentHistoryChartProps) {
  if (!history || history.length === 0) {
    return (
      <div className="flex items-center justify-center h-[200px] text-sm text-slate-400">
        History data will appear after daily snapshots accumulate.
      </div>
    );
  }

  const data = history.map((h) => ({
    ...h,
    label: formatDateLabel(h.date),
  }));

  // Sample ~12 x-axis labels evenly
  const step = Math.max(1, Math.floor(data.length / 12));
  const visibleTicks = data
    .filter((_, i) => i % step === 0 || i === data.length - 1)
    .map((d) => d.label);

  // Current score for tooltip header
  const latest = data[data.length - 1];

  return (
    <ResponsiveContainer width="100%" height={200}>
      <AreaChart data={data} margin={{ top: 8, right: 12, left: 0, bottom: 0 }}>
        {/* Zone background bands */}
        <ReferenceArea y1={0} y2={30} fill="#fef2f2" fillOpacity={0.6} />
        <ReferenceArea y1={30} y2={45} fill="#fffbeb" fillOpacity={0.5} />
        <ReferenceArea y1={45} y2={55} fill="#f8fafc" fillOpacity={0.5} />
        <ReferenceArea y1={55} y2={70} fill="#ecfdf5" fillOpacity={0.5} />
        <ReferenceArea y1={70} y2={100} fill="#d1fae5" fillOpacity={0.5} />

        <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" strokeOpacity={0.5} vertical={false} />

        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          ticks={visibleTicks}
        />
        <YAxis
          domain={[0, 100]}
          ticks={[0, 30, 45, 55, 70, 100]}
          tick={{ fontSize: 9, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={28}
        />

        {/* Zone labels on right */}
        <YAxis
          yAxisId="zones"
          orientation="right"
          domain={[0, 100]}
          ticks={[15, 37, 50, 62, 85]}
          tickFormatter={(v: number) => {
            if (v === 15) return "Bear";
            if (v === 37) return "Weak";
            if (v === 50) return "Neutral";
            if (v === 62) return "Bullish";
            if (v === 85) return "Strong";
            return "";
          }}
          tick={{ fontSize: 8, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={40}
        />

        <Tooltip
          contentStyle={{
            fontSize: 12,
            borderRadius: 8,
            border: "1px solid #e2e8f0",
            boxShadow: "0 2px 8px rgba(0,0,0,0.08)",
          }}
          formatter={(value: number) => {
            const zone = zoneLabel(value);
            return [
              <span key="score" style={{ color: zoneColor(value), fontWeight: 600 }}>
                {value.toFixed(1)} — {zone}
              </span>,
              "Score",
            ];
          }}
          labelFormatter={(label: string) => label}
        />

        <defs>
          <linearGradient id="sentimentGradient" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={zoneColor(latest?.score ?? 50)} stopOpacity={0.3} />
            <stop offset="100%" stopColor={zoneColor(latest?.score ?? 50)} stopOpacity={0.05} />
          </linearGradient>
        </defs>

        <Area
          type="monotone"
          dataKey="score"
          stroke={zoneColor(latest?.score ?? 50)}
          strokeWidth={2.5}
          fill="url(#sentimentGradient)"
          dot={false}
          activeDot={{ r: 4, fill: zoneColor(latest?.score ?? 50), stroke: "#fff", strokeWidth: 2 }}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}
