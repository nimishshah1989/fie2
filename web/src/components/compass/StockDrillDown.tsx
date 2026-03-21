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
import { ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import type { StockRS, SectorRS, Quadrant, CompassAction } from "@/lib/compass-types";

const QUADRANT_COLORS: Record<Quadrant, string> = {
  LEADING: "#059669",
  IMPROVING: "#2563eb",
  WEAKENING: "#ea580c",
  LAGGING: "#dc2626",
};

const ACTION_BADGE: Record<CompassAction, { bg: string; text: string }> = {
  BUY: { bg: "bg-emerald-100", text: "text-emerald-700" },
  ACCUMULATE: { bg: "bg-teal-100", text: "text-teal-700" },
  WATCH: { bg: "bg-blue-100", text: "text-blue-700" },
  HOLD: { bg: "bg-amber-100", text: "text-amber-700" },
  SELL: { bg: "bg-red-100", text: "text-red-700" },
  AVOID: { bg: "bg-slate-100", text: "text-slate-600" },
  EXIT: { bg: "bg-red-200", text: "text-red-800" },
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
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm">
      <p className="font-semibold text-slate-900">{s.company_name}</p>
      <p className="text-xs text-slate-500">{s.ticker}</p>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 mt-1.5">
        <span className="text-slate-500">RS Score</span>
        <span className="font-mono font-medium text-right">{s.rs_score}</span>
        <span className="text-slate-500">Momentum</span>
        <span className={`font-mono font-medium text-right ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
          {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
        </span>
        <span className="text-slate-500">Volume</span>
        <span className="text-right">{s.volume_signal?.replace("_", " ") || "—"}</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: QUADRANT_COLORS[s.quadrant] }}>
          {s.action}
        </span>
        {s.pe_ratio && (
          <>
            <span className="text-slate-500">P/E</span>
            <span className="font-mono text-right">{s.pe_ratio}</span>
          </>
        )}
        {s.stop_loss_pct && (
          <>
            <span className="text-slate-500">Stop Loss</span>
            <span className="font-mono text-right">{s.stop_loss_pct}%</span>
          </>
        )}
      </div>
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

  const sectorAction = ACTION_BADGE[sectorInfo.action];

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-3 mb-2">
          <Button variant="ghost" size="sm" onClick={onBack} className="h-8 px-2">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <h2 className="text-lg font-bold text-slate-900">{sectorInfo.display_name}</h2>
          <span className={`${sectorAction.bg} ${sectorAction.text} rounded-full px-2.5 py-0.5 text-xs font-semibold`}>
            {sectorInfo.action}
          </span>
        </div>
        <div className="flex items-center gap-6 text-sm">
          <span className="text-slate-500">RS: <span className="font-mono font-semibold text-slate-900">{sectorInfo.rs_score}</span></span>
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

      {/* Empty state — data not yet backfilled */}
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
            <XAxis type="number" dataKey="x" name="RS Score" domain={[0, 100]} tick={{ fontSize: 11, fill: "#94a3b8" }}
              label={{ value: "RS Score (vs Sector)", position: "bottom", offset: 0, style: { fontSize: 11, fill: "#64748b" } }} />
            <YAxis type="number" dataKey="y" name="Momentum" domain={[-50, 50]} tick={{ fontSize: 11, fill: "#94a3b8" }}
              label={{ value: "Momentum", angle: -90, position: "insideLeft", style: { fontSize: 11, fill: "#64748b" } }} />
            <ZAxis type="number" dataKey="z" range={[150, 800]} />
            <ReferenceLine x={50} stroke="#94a3b8" strokeDasharray="4 4" />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Tooltip content={<StockTooltip />} />
            <Scatter data={chartData}>
              {chartData.map((entry, i) => (
                <Cell key={`stock-${i}`} fill={QUADRANT_COLORS[entry.quadrant]} fillOpacity={0.7}
                  stroke={QUADRANT_COLORS[entry.quadrant]} strokeWidth={1} />
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
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">RS</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Mtm</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Volume</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">P/E</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Wt%</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Stop</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((s) => {
                const badge = ACTION_BADGE[s.action];
                return (
                  <tr key={s.ticker} className="border-b border-slate-50 hover:bg-slate-25 transition-colors">
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-slate-900">{s.ticker}</p>
                      <p className="text-xs text-slate-400 truncate max-w-[180px]">{s.company_name}</p>
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`${badge.bg} ${badge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>
                        {s.action}
                      </span>
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono font-medium">{s.rs_score}</td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
                    </td>
                    <td className="px-3 py-2.5 text-center text-xs">
                      {s.volume_signal?.replace("_", " ") || "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono">{s.pe_ratio ?? "—"}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-500">
                      {s.weight_pct ? `${s.weight_pct.toFixed(1)}` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-500">
                      {s.stop_loss_pct ? `${s.stop_loss_pct}%` : "—"}
                    </td>
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
