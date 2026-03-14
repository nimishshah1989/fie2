"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ReferenceLine,
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

export function SentimentHistoryChart({ history }: SentimentHistoryChartProps) {
  if (!history || history.length === 0) {
    return (
      <div className="flex items-center justify-center h-[120px] text-sm text-slate-400">
        History data will appear after daily snapshots accumulate.
      </div>
    );
  }

  const data = history.map((h) => ({
    ...h,
    label: formatDateLabel(h.date),
  }));

  return (
    <ResponsiveContainer width="100%" height={120}>
      <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 0 }}>
        <XAxis
          dataKey="label"
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 10, fill: "#94a3b8" }}
          axisLine={false}
          tickLine={false}
          width={28}
        />
        <ReferenceLine y={30} stroke="#e24b4a" strokeDasharray="3 3" strokeOpacity={0.4} />
        <ReferenceLine y={45} stroke="#ef9f27" strokeDasharray="3 3" strokeOpacity={0.4} />
        <ReferenceLine y={55} stroke="#888780" strokeDasharray="3 3" strokeOpacity={0.4} />
        <ReferenceLine y={70} stroke="#1d9e75" strokeDasharray="3 3" strokeOpacity={0.4} />
        <Tooltip
          contentStyle={{ fontSize: 12, borderRadius: 8, border: "1px solid #e2e8f0" }}
          formatter={(value: number) => [`${value.toFixed(1)}`, "Score"]}
          labelFormatter={(label: string) => label}
        />
        <Line
          type="monotone"
          dataKey="score"
          stroke="#0d9488"
          strokeWidth={2}
          dot={false}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
