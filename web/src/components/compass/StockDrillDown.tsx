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
import { ArrowLeft, Info } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { StockRS, SectorRS, CompassAction } from "@/lib/compass-types";
import { actionLabel } from "@/lib/compass-types";

const ACTION_COLORS: Record<string, string> = {
  BUY: "#059669",
  HOLD: "#d97706",
  WATCH_EMERGING: "#2563eb",
  WATCH_RELATIVE: "#0284c7",
  WATCH_EARLY: "#4f46e5",
  AVOID: "#ea580c",
  SELL: "#dc2626",
};

const ACTION_BADGE: Record<CompassAction, { bg: string; text: string }> = {
  BUY: { bg: "bg-emerald-100", text: "text-emerald-700" },
  HOLD: { bg: "bg-amber-100", text: "text-amber-700" },
  WATCH_EMERGING: { bg: "bg-blue-100", text: "text-blue-700" },
  WATCH_RELATIVE: { bg: "bg-sky-100", text: "text-sky-700" },
  WATCH_EARLY: { bg: "bg-indigo-100", text: "text-indigo-700" },
  AVOID: { bg: "bg-orange-100", text: "text-orange-700" },
  SELL: { bg: "bg-red-100", text: "text-red-700" },
};

interface Props {
  sectorInfo: SectorRS;
  stocks: StockRS[];
  loadingStocks?: boolean;
  onBack: () => void;
}

function StockTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: StockRS & { x: number; y: number } }> }) {
  if (!active || !payload?.[0]) return null;
  const s = payload[0].payload;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm max-w-[280px]">
      <p className="font-semibold text-slate-900">{s.company_name}</p>
      <p className="text-xs text-slate-500">{s.ticker}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1.5">
        <span className="text-slate-500">RS Score</span>
        <span className={`font-mono font-medium text-right ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{s.rs_score > 0 ? "+" : ""}{s.rs_score}%</span>
        <span className="text-slate-500">Abs Return</span>
        <span className={`font-mono font-medium text-right ${(s.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {s.absolute_return != null ? `${s.absolute_return > 0 ? "+" : ""}${s.absolute_return.toFixed(1)}%` : "—"}
        </span>
        <span className="text-slate-500">Momentum</span>
        <span className={`font-mono font-medium text-right ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
        </span>
        <span className="text-slate-500">Volume</span>
        <span className="text-right">{s.volume_signal?.replace("_", " ") || "—"}</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: ACTION_COLORS[s.action] || "#334155" }}>
          {actionLabel(s.action)}
        </span>
        {s.pe_ratio && (
          <>
            <span className="text-slate-500">P/E</span>
            <span className="font-mono text-right">{s.pe_ratio} · {s.pe_zone || ""}</span>
          </>
        )}
      </div>
      <p className="text-xs text-slate-500 mt-2 italic">{s.action_reason}</p>
    </div>
  );
}

export function StockDrillDown({ sectorInfo, stocks, loadingStocks, onBack }: Props) {
  const chartData = stocks.map((s) => ({
    ...s,
    x: s.rs_score,
    y: s.rs_momentum,
    z: s.pe_ratio ? Math.max(5, 80 - s.pe_ratio) : 25,
  }));

  const sectorBadge = ACTION_BADGE[sectorInfo.action] || ACTION_BADGE.HOLD;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-3 mb-2">
          <Button variant="ghost" size="sm" onClick={onBack} className="h-8 px-2">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <h2 className="text-lg font-bold text-slate-900">{sectorInfo.display_name}</h2>
          <span className={`${sectorBadge.bg} ${sectorBadge.text} rounded-full px-2.5 py-0.5 text-xs font-semibold`}>
            {actionLabel(sectorInfo.action)}
          </span>
          {sectorInfo.pe_zone && (
            <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
              sectorInfo.pe_zone === "VALUE" ? "bg-emerald-100 text-emerald-700" :
              sectorInfo.pe_zone === "FAIR" ? "bg-slate-100 text-slate-600" :
              sectorInfo.pe_zone === "STRETCHED" ? "bg-amber-100 text-amber-700" :
              "bg-red-100 text-red-700"
            }`}>
              {sectorInfo.pe_zone}{sectorInfo.pe_ratio ? ` (P/E ${sectorInfo.pe_ratio.toFixed(0)})` : ""}
            </span>
          )}
        </div>
        <p className="text-xs text-slate-500 italic ml-12 mb-2">{sectorInfo.action_reason}</p>
        <div className="flex items-center gap-6 text-sm ml-12">
          <span className="text-slate-500">RS: <span className={`font-mono font-semibold ${sectorInfo.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{sectorInfo.rs_score > 0 ? "+" : ""}{sectorInfo.rs_score}%</span></span>
          <span className="text-slate-500">Abs: <span className={`font-mono font-semibold ${(sectorInfo.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>{sectorInfo.absolute_return != null ? `${sectorInfo.absolute_return > 0 ? "+" : ""}${sectorInfo.absolute_return.toFixed(1)}%` : "—"}</span></span>
          <span className="text-slate-500">Momentum: <span className={`font-mono font-semibold ${sectorInfo.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>{sectorInfo.rs_momentum > 0 ? "+" : ""}{sectorInfo.rs_momentum}</span></span>
          <span className="text-slate-500">Vol: <span className="font-medium">{sectorInfo.volume_signal?.replace("_", " ") || "—"}</span></span>
          {sectorInfo.etfs.length > 0 && (
            <span className="text-slate-500">ETF: <span className="font-semibold text-teal-600">{sectorInfo.etfs.join(", ")}</span></span>
          )}
        </div>
      </div>

      {/* Loading state */}
      {loadingStocks && (
        <div className="space-y-4">
          <Skeleton className="h-[380px] w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      )}

      {/* Empty state */}
      {!loadingStocks && stocks.length === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <p className="text-sm text-slate-500 font-medium">Stock data is being backfilled</p>
          <p className="text-xs text-slate-400 mt-1">
            Price history for constituent stocks is loading. This takes a few minutes on first startup.
            Try again shortly or click Refresh RS.
          </p>
        </div>
      )}

      {/* Scatter chart + table */}
      {!loadingStocks && stocks.length > 0 && (
      <>
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <ResponsiveContainer width="100%" height={380}>
          <ScatterChart margin={{ top: 15, right: 25, bottom: 20, left: 15 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis type="number" dataKey="x" name="RS Score" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}%`}
              label={{ value: "RS Score (% vs Sector)", position: "bottom", offset: 0, style: { fontSize: 11, fill: "#64748b" } }} />
            <YAxis type="number" dataKey="y" name="Momentum" domain={["auto", "auto"]} tick={{ fontSize: 11, fill: "#94a3b8" }}
              tickFormatter={(v: number) => `${v > 0 ? "+" : ""}${v.toFixed(0)}`}
              label={{ value: "Momentum (4w change)", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#64748b" } }} />
            <ZAxis type="number" dataKey="z" range={[150, 800]} />
            <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Tooltip content={<StockTooltip />} />
            <Scatter data={chartData}>
              {chartData.map((entry, i) => (
                <Cell key={`stock-${i}`} fill={ACTION_COLORS[entry.action] || "#94a3b8"} fillOpacity={0.7}
                  stroke={ACTION_COLORS[entry.action] || "#94a3b8"} strokeWidth={1} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Stock table */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50">
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-3">Stock</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Action</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Relative Strength: % outperformance vs sector index">RS %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Absolute return of the stock over the selected period">Abs %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="4-week change in RS Score — is relative strength improving or fading?">Momentum</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Volume trend: 20d avg vs 60d avg + price direction">Volume</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3" title="Trailing 12-month P/E ratio">P/E</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3 min-w-[200px]">Reason</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => {
                const badge = ACTION_BADGE[s.action] || ACTION_BADGE.HOLD;
                return (
                  <tr key={s.ticker} className="border-b border-slate-50 hover:bg-slate-25 transition-colors">
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-slate-900">{s.ticker}</p>
                      <p className="text-xs text-slate-400 truncate max-w-[180px]">{s.company_name}</p>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`${badge.bg} ${badge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>
                        {actionLabel(s.action)}
                      </span>
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{s.rs_score > 0 ? "+" : ""}{s.rs_score}%</td>
                    <td className={`px-3 py-2.5 text-right font-mono ${(s.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.absolute_return != null ? `${s.absolute_return > 0 ? "+" : ""}${s.absolute_return.toFixed(1)}%` : "—"}
                    </td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
                    </td>
                    <td className="px-3 py-2.5 text-center text-xs">
                      {s.volume_signal?.replace("_", " ") || "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">
                      {s.pe_ratio ?? "—"}
                      {s.pe_zone && <span className="text-xs text-slate-400 ml-1">· {s.pe_zone}</span>}
                    </td>
                    <td className="px-3 py-2.5 text-xs text-slate-500 italic">{s.action_reason}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      </>
      )}
    </div>
  );
}
