"use client";

import { useState } from "react";
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
import { useCompassETFs, useCompassStocks } from "@/hooks/use-compass";
import type { ETFRS, StockRS, CompassAction, Period } from "@/lib/compass-types";
import { actionLabel, volumeDescription, volumeLabel, peZoneLabel } from "@/lib/compass-types";

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
  base: string;
  period: Period;
}

function ETFTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: ETFRS & { x: number; y: number } }> }) {
  if (!active || !payload?.[0]) return null;
  const e = payload[0].payload;
  return (
    <div className="bg-white border border-slate-200 rounded-lg shadow-lg p-3 text-sm max-w-[280px]">
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
        <span className="text-right">{volumeLabel(e.volume_signal)}</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: ACTION_COLORS[e.action] || "#334155" }}>{actionLabel(e.action)}</span>
        {e.pe_ratio != null && (
          <>
            <span className="text-slate-500">P/E</span>
            <span className="font-mono text-right">{peZoneLabel(e.pe_zone, e.pe_ratio)}</span>
          </>
        )}
      </div>
      <p className="text-xs text-slate-500 mt-2 italic">{e.action_reason}</p>
      {e.parent_sector && <p className="text-xs text-slate-400 mt-1">Click to see constituent stocks</p>}
    </div>
  );
}

// ── ETF Stock Drill-Down ───────────────────────────────

function ETFStockDrillDown({ etfInfo, stocks, loading, onBack }: {
  etfInfo: ETFRS;
  stocks: StockRS[];
  loading: boolean;
  onBack: () => void;
}) {
  const badge = ACTION_BADGE[etfInfo.action] || ACTION_BADGE.HOLD;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <div className="flex items-center gap-3 mb-2">
          <Button variant="ghost" size="sm" onClick={onBack} className="h-8 px-2">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <h2 className="text-lg font-bold text-slate-900">{etfInfo.ticker}</h2>
          <span className={`${badge.bg} ${badge.text} rounded-full px-2.5 py-0.5 text-xs font-semibold`}>
            {actionLabel(etfInfo.action)}
          </span>
          {etfInfo.sector_name && (
            <span className="text-xs text-slate-400">tracks {etfInfo.sector_name}</span>
          )}
        </div>
        <p className="text-xs text-slate-500 italic ml-12 mb-2">{etfInfo.action_reason}</p>
        <div className="flex items-center gap-6 text-sm ml-12">
          <span className="text-slate-500">RS: <span className={`font-mono font-semibold ${etfInfo.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{etfInfo.rs_score > 0 ? "+" : ""}{etfInfo.rs_score.toFixed(1)}%</span></span>
          <span className="text-slate-500">Abs: <span className={`font-mono font-semibold ${(etfInfo.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>{etfInfo.absolute_return != null ? `${etfInfo.absolute_return > 0 ? "+" : ""}${etfInfo.absolute_return.toFixed(1)}%` : "—"}</span></span>
          <span className="text-slate-500">Momentum: <span className={`font-mono font-semibold ${etfInfo.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>{etfInfo.rs_momentum > 0 ? "+" : ""}{etfInfo.rs_momentum.toFixed(1)}</span></span>
          <span className="text-slate-500">Vol: <span className="font-medium">{volumeLabel(etfInfo.volume_signal)}</span></span>
        </div>
      </div>

      {loading && (
        <div className="space-y-4">
          <Skeleton className="h-[380px] w-full rounded-xl" />
          <Skeleton className="h-48 w-full rounded-xl" />
        </div>
      )}

      {!loading && stocks.length === 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
          <p className="text-sm text-slate-500 font-medium">Constituent stock data is being backfilled</p>
          <p className="text-xs text-slate-400 mt-1">
            Price history for stocks in {etfInfo.sector_name || etfInfo.ticker} is loading. Try again shortly.
          </p>
        </div>
      )}

      {!loading && stocks.length > 0 && (
      <>
        {/* Scatter chart */}
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-2">
            Constituent Stocks — {etfInfo.sector_name || etfInfo.ticker} ({stocks.length} stocks)
          </h3>
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
              <Tooltip content={<StockTooltipInner />} />
              <Scatter data={stocks.map((s) => ({ ...s, x: s.rs_score, y: s.rs_momentum, z: s.pe_ratio ? Math.max(5, 80 - s.pe_ratio) : 25 }))}>
                {stocks.map((entry, i) => (
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
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">RS %</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Abs %</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Momentum</th>
                  <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Volume</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">P/E</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3 min-w-[200px]">Reason</th>
                </tr>
              </thead>
              <tbody>
                {stocks.map((s) => {
                  const sBadge = ACTION_BADGE[s.action] || ACTION_BADGE.HOLD;
                  return (
                    <tr key={s.ticker} className="border-b border-slate-50 hover:bg-slate-25 transition-colors">
                      <td className="px-4 py-2.5">
                        <p className="font-medium text-slate-900">{s.ticker}</p>
                        <p className="text-xs text-slate-400 truncate max-w-[180px]">{s.company_name}</p>
                      </td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`${sBadge.bg} ${sBadge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>{actionLabel(s.action)}</span>
                      </td>
                      <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_score > 0 ? "text-emerald-600" : "text-red-600"}`}>{s.rs_score > 0 ? "+" : ""}{s.rs_score}%</td>
                      <td className={`px-3 py-2.5 text-right font-mono ${(s.absolute_return ?? 0) > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {s.absolute_return != null ? `${s.absolute_return > 0 ? "+" : ""}${s.absolute_return.toFixed(1)}%` : "—"}
                      </td>
                      <td className={`px-3 py-2.5 text-right font-mono font-medium ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>
                        {s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}
                      </td>
                      <td className="px-3 py-2.5 text-center text-xs" title={volumeDescription(s.volume_signal)}>
                        {volumeDescription(s.volume_signal)}
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

function StockTooltipInner({ active, payload }: { active?: boolean; payload?: Array<{ payload: StockRS & { x: number; y: number } }> }) {
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
        <span className={`font-mono font-medium text-right ${s.rs_momentum > 0 ? "text-emerald-600" : "text-red-600"}`}>{s.rs_momentum > 0 ? "+" : ""}{s.rs_momentum}</span>
        <span className="text-slate-500">Action</span>
        <span className="font-semibold text-right" style={{ color: ACTION_COLORS[s.action] || "#334155" }}>{actionLabel(s.action)}</span>
      </div>
      <p className="text-xs text-slate-500 mt-2 italic">{s.action_reason}</p>
    </div>
  );
}

// ── Main ETF View ──────────────────────────────────────

export function ETFView({ base, period }: Props) {
  const { etfs, isLoading } = useCompassETFs(base, period);
  const [selectedETF, setSelectedETF] = useState<ETFRS | null>(null);

  // Fetch constituent stocks when an ETF with a parent sector is selected
  const { stocks, isLoading: loadingStocks } = useCompassStocks(
    selectedETF?.parent_sector || null, base, period
  );

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

  // Show drill-down if an ETF with a parent sector is selected
  if (selectedETF) {
    return (
      <ETFStockDrillDown
        etfInfo={selectedETF}
        stocks={stocks}
        loading={loadingStocks}
        onBack={() => setSelectedETF(null)}
      />
    );
  }

  const chartData = etfs.map((e) => ({
    ...e,
    x: e.rs_score,
    y: e.rs_momentum,
    z: e.pe_ratio ? Math.max(5, 100 - e.pe_ratio) : 30,
  }));

  const handleETFClick = (data: { payload?: ETFRS }) => {
    const etf = data?.payload;
    if (!etf) return;
    if (etf.parent_sector) {
      setSelectedETF(etf);
    }
  };

  return (
    <div className="space-y-4">
      {/* Scatter chart */}
      <div className="bg-white rounded-xl border border-slate-200 p-4">
        <h3 className="text-sm font-semibold text-slate-900 mb-2">
          ETF Relative Strength ({etfs.length} ETFs tracked)
          <span className="text-xs text-slate-400 font-normal ml-2">Click sector ETFs to see constituent stocks</span>
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
            <ZAxis type="number" dataKey="z" range={[200, 1200]} />
            <ReferenceLine x={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <ReferenceLine y={0} stroke="#94a3b8" strokeDasharray="4 4" />
            <Tooltip content={<ETFTooltip />} />
            <Scatter data={chartData} onClick={handleETFClick} cursor="pointer">
              {chartData.map((entry, i) => (
                <Cell key={`etf-${i}`} fill={ACTION_COLORS[entry.action] || "#94a3b8"} fillOpacity={0.7}
                  stroke={ACTION_COLORS[entry.action] || "#94a3b8"} strokeWidth={entry.parent_sector ? 2 : 1} />
              ))}
            </Scatter>
          </ScatterChart>
        </ResponsiveContainer>
        <div className="flex items-center gap-4 px-6 text-xs -mt-2">
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-emerald-600 inline-block" /> BUY</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-amber-600 inline-block" /> HOLD</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-blue-600 inline-block" /> WATCH</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-orange-600 inline-block" /> AVOID</span>
          <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-full bg-red-600 inline-block" /> SELL</span>
        </div>
        <p className="text-xs text-slate-400 ml-auto">Bubble size = Value (lower P/E = bigger)</p>
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
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">RS %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Abs %</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Momentum</th>
                <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">Volume</th>
                <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3">P/E</th>
                <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-3 min-w-[200px]">Reason</th>
              </tr>
            </thead>
            <tbody>
              {etfs
                .sort((a, b) => b.rs_score - a.rs_score)
                .map((e) => {
                  const badge = ACTION_BADGE[e.action] || ACTION_BADGE.HOLD;
                  return (
                    <tr
                      key={e.ticker}
                      onClick={() => e.parent_sector ? setSelectedETF(e) : undefined}
                      className={`border-b border-slate-50 transition-colors ${
                        e.parent_sector ? "hover:bg-slate-50 cursor-pointer" : "hover:bg-slate-25"
                      }`}
                    >
                      <td className="px-4 py-2.5">
                        <span className="font-semibold text-slate-900">{e.ticker}</span>
                        {e.parent_sector && <span className="text-xs text-teal-500 ml-1.5">→</span>}
                      </td>
                      <td className="px-3 py-2.5 text-slate-600 text-xs">{e.sector_name || "—"}</td>
                      <td className="px-3 py-2.5 text-center">
                        <span className={`${badge.bg} ${badge.text} rounded-full px-2 py-0.5 text-xs font-semibold`}>{actionLabel(e.action)}</span>
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
                      <td className="px-3 py-2.5 text-center text-xs text-slate-500" title={volumeDescription(e.volume_signal)}>
                        {volumeDescription(e.volume_signal)}
                      </td>
                      <td className="px-3 py-2.5 text-right font-mono">
                        {e.pe_ratio != null ? e.pe_ratio.toFixed(0) : "—"}
                        {e.pe_zone && <span className="text-xs text-slate-400 ml-1">· {e.pe_zone.charAt(0) + e.pe_zone.slice(1).toLowerCase()}</span>}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-500 italic">{e.action_reason}</td>
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
