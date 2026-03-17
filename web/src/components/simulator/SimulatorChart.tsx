"use client";

import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ReferenceDot,
  CartesianGrid,
} from "recharts";
import type { TimelinePoint } from "@/lib/simulator-types";

interface Props {
  timeline: TimelinePoint[];
  triggerDates: string[];
}

function fmtINR(v: number): string {
  if (v >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (v >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  if (v >= 1e3) return `₹${(v / 1e3).toFixed(0)}K`;
  return `₹${v.toFixed(0)}`;
}

function fmtDate(d: string): string {
  return new Date(d).toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

export function SimulatorChart({ timeline, triggerDates }: Props) {
  const triggerSet = new Set(triggerDates);
  const triggers = timeline.filter((t) => triggerSet.has(t.date));

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <p className="text-sm font-semibold text-slate-700 mb-4">Portfolio Value Over Time</p>
      <ResponsiveContainer width="100%" height={360}>
        <ComposedChart data={timeline} margin={{ top: 10, right: 10, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tickFormatter={fmtDate}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            interval="equidistantPreserveStart"
          />
          <YAxis
            tickFormatter={fmtINR}
            tick={{ fontSize: 11, fill: "#94a3b8" }}
            axisLine={false}
            tickLine={false}
            width={65}
          />
          <Tooltip
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const d = payload[0]?.payload as TimelinePoint;
              return (
                <div className="bg-white border border-slate-200 rounded-lg p-3 shadow-lg text-xs">
                  <p className="font-semibold text-slate-700 mb-2">
                    {new Date(label).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" })}
                  </p>
                  <div className="space-y-1">
                    <p className="text-teal-600">
                      Enhanced: {fmtINR(d.enhanced_value)}
                      <span className="text-slate-400 ml-1">(inv: {fmtINR(d.enhanced_invested)})</span>
                    </p>
                    <p className="text-blue-600">
                      Regular: {fmtINR(d.regular_value)}
                      <span className="text-slate-400 ml-1">(inv: {fmtINR(d.regular_invested)})</span>
                    </p>
                    <p className="text-slate-500">NAV: ₹{d.nav.toFixed(2)}</p>
                    {d.breadth_count !== null && (
                      <p className="text-slate-500 mt-1">
                        Breadth: {d.breadth_count}/{d.breadth_total}
                        {d.is_trigger && <span className="text-amber-600 font-semibold ml-1">TOP-UP</span>}
                        {d.in_cooloff && <span className="text-orange-400 font-semibold ml-1">COOLOFF</span>}
                      </p>
                    )}
                  </div>
                </div>
              );
            }}
          />
          <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: "12px" }} />
          <Area
            type="monotone"
            dataKey="enhanced_value"
            name="Enhanced SIP Value"
            fill="#0d948820"
            stroke="#0d9488"
            strokeWidth={2}
          />
          <Area
            type="monotone"
            dataKey="regular_value"
            name="Regular SIP Value"
            fill="#2563eb15"
            stroke="#2563eb"
            strokeWidth={1.5}
            strokeDasharray="4 2"
          />
          <Line
            type="monotone"
            dataKey="enhanced_invested"
            name="Enhanced Invested"
            stroke="#0d9488"
            strokeWidth={1}
            strokeDasharray="2 2"
            dot={false}
            opacity={0.4}
          />
          <Line
            type="monotone"
            dataKey="regular_invested"
            name="Regular Invested"
            stroke="#2563eb"
            strokeWidth={1}
            strokeDasharray="2 2"
            dot={false}
            opacity={0.4}
          />
          {triggers.map((t) => (
            <ReferenceDot
              key={t.date}
              x={t.date}
              y={t.enhanced_value}
              r={4}
              fill="#f59e0b"
              stroke="#f59e0b"
            />
          ))}
        </ComposedChart>
      </ResponsiveContainer>
      {triggers.length > 0 && (
        <p className="text-[10px] text-slate-400 mt-2 text-center">
          Amber dots = top-up dates &middot; 1-month cool-off enforced between top-ups
        </p>
      )}
    </div>
  );
}
