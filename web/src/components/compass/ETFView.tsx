"use client";

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  ZAxis,
} from "recharts";
import { Skeleton } from "@/components/ui/skeleton";
import { useCompassETFs } from "@/hooks/use-compass";
import type { ETFRS, Quadrant, CompassAction, Period } from "@/lib/compass-types";

const QUADRANT_COLORS: Record<Quadrant, string> = {
  LEADING: "#059669",
  IMPROVING: "#2563eb",
  WEAKENING: "#ea580c",
  LAGGING: "#dc2626",
};

const ACTION_BADGE: Record<CompassAction, { bg: string; text: string }> = {
  BUY: { bg: "bg-emerald-100", text: "text-emerald-700" },
  HOLD: { bg: "bg-amber-100", text: "text-amber-700" },
  WATCH: { bg: "bg-blue-100", text: "text-blue-700" },
  SELL: { bg: "bg-red-100", text: "text-red-700" },
};

interface Props {
  base: string;
  period: Period;
}

function ETFTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ETFRS & { x: number; y: number } }> }) {
  if (!active || !payload?.[0]) return null;
  const e = payload[0].payload;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-slate-900">{e.ticker}</p>
      {e.sector_name && <p className="text-xs text-slate-500">{e.sector_name}</p>}
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1.5">
        <span className="text-slate-500">RS Score</span>
        <span className={`font-mono font-medium text-right ${e.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {e.rs_score > 0 ? "+" : ""}{e.rs_score.toFixed(1)}%
        </span>
        <span className="text-slate-500">Abs Return</span>
        <span className={`font-mono font-medium text-right ${(e.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {e.absolute_return != null ? `${e.absolute_return > 0 ? "+" : ""}${e.absolute_return.toFixed(1)}%` : "—"}
        </span>
        <span className="text-slate-500">Momentum</span>
        <span className={`font-mono font-medium text-right ${e.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {e.rs_momentum > 0 ? "+" : ""}{e.rs_momentum.toFixed(1)}
        </span>
        <span className="text-slate-500">Volume</span>
        <span className="text-right">{e.volume_signal?.replace("_", " ") || "—"}</span>
        <span className="text-slate-500">Conviction</span>
        <span className="font-mono font-medium text-right">{e.conviction ?? 0}/100</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: QUADRANT_COLORS[e.quadrant] }}>{e.action}</span>
      </div>
    </div>
  );
}

export function ETFView({ base, period }: Props) {
  const { etfs, isLoading } = useCompassETFs(base, period);

  if (isLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-[400px] w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    );
  }

  if (etfs.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <p className="text-sm text-slate-500">No ETF data available yet. ETF prices are being backfilled.</p>
      </div>
    );
  }

  const chartData = etfs.map((e) => ({
    ...e,
    x: e.rs_score,
    y: e.rs_momentum,
    z: 30,
  }));

  // Group by action for the summary below
  const byAction: Record<string, ETFRS[]> = {};
  for (const e of etfs) {
    if (!byAction[e.action]) byAction[e.action] = [];
    byAction[e.action].push(e);
  }

  return (
    <div className="space-y-4">
      {/* Scatter chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-900 mb-2">
          ETF Relative Strength ({etfs.length} ETFs tracked)
        </h3>
        <ResponsiveContainer width="100%" height={400}>
          <ScatterChart margin={{ top: 15, right: 25, bottom: 20, left: 15 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" dataKey="x" name="RS Score" domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
              label={{ value: "RS Score (% vs benchmark)", position: "bottom", offset: 0, style: { fontSize: 11, fill: "#64748b" } }} />
            <YAxis type="number" dataKey="y" name="Momentum" domain={["auto", "auto"]}
              tick={{ fontSize: 11, fill: "#94a3b8" }}
              label={{ value: "Momentum", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#64748b" } }} />
            <ZAxis type="number" dataKey="z" range={[200, 400]} />
            <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Tooltip content={<ETFTooltip />} />
            <Scatter data={chartData} cursor="pointer">
              {chartData.map((entry, i) => (
                <Cell key={`etf-${i}`} fill={QUADRANT_COLORS[entry.quadrant]} fillOpacity={0.7}
                  stroke={QUADRANT_COLORS[entry.quadrant]} strokeWidth={1.5} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 px-6 text-xs -mt-2">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-emerald-600 inline-block" /> LEADING</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-blue-600 inline-block" /> IMPROVING</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-orange-600 inline-block" /> WEAKENING</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-600 inline-block" /> LAGGING</span>
        </div>
      </div>

      {/* ETF table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">ETF</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Sector</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Action</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Conviction score (0-100) combining RS, momentum, volume, absolute return, and market regime">Score</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Relative Strength: % outperformance vs NIFTY benchmark">RS %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Absolute return of this ETF over the period">Abs %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="4-week change in RS Score — is relative strength improving or fading?">Momentum</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Volume trend: 20d avg vs 60d avg + price direction">Volume</th>
              </tr>
            </thead>
            <tbody>
              {etfs
                .sort((a, b) => (b.conviction ?? 0) - (a.conviction ?? 0))
                .map((e) => {
                  const badge = ACTION_BADGE[e.action];
                  return (
                    <tr key={e.ticker} className="border-b border-slate-50 hover:bg-slate-25 transition-colors">
                      <td className="px-4 py-2.5 font-semibold text-slate-900">{e.ticker}</td>
                      <td className="px-3 py-2.5 text-slate-600 text-xs">{e.sector_name || "—"}</td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`${badge.bg} ${badge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>{e.action}</span>
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono font-medium">
                        <span className={`${(e.conviction ?? 0) >= 60 ? "text-emerald-600" : (e.conviction ?? 0) >= 40 ? "text-amber-600" : "text-red-600"}`}>
                          {e.conviction ?? 0}
                        </span>
                      </td>
                      <td className={`px-3 py-2.5 text-right font-mono font-medium ${e.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {e.rs_score > 0 ? "+" : ""}{e.rs_score.toFixed(1)}
                      </td>
                      <td className={`px-3 py-2.5 text-right font-mono ${(e.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {e.absolute_return != null ? `${e.absolute_return > 0 ? "+" : ""}${e.absolute_return.toFixed(1)}%` : "—"}
                      </td>
                      <td className={`px-3 py-2.5 text-right font-mono font-medium ${e.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {e.rs_momentum > 0 ? "+" : ""}{e.rs_momentum.toFixed(1)}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs text-slate-500">{e.volume_signal?.replace("_", " ") || "—"}</td>
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
