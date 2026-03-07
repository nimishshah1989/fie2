"use client";

import type { PmsMetric } from "@/lib/pms-types";

interface PmsPerformanceTableProps {
  metrics: PmsMetric[];
  asOfDate: string | null;
}

function fmtPct(v: number | null): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function fmtRatio(v: number | null): string {
  if (v == null) return "—";
  return v.toFixed(2);
}

function colorPct(v: number | null): string {
  if (v == null) return "text-slate-400";
  return v >= 0 ? "text-emerald-600" : "text-red-600";
}

const PERIOD_LABELS: Record<string, string> = {
  "1M": "1 Month",
  "3M": "3 Months",
  "6M": "6 Months",
  "1Y": "1 Year",
  "2Y": "2 Years",
  "3Y": "3 Years",
  "4Y": "4 Years",
  "5Y": "5 Years",
  "SI": "Since Inception",
};

export function PmsPerformanceTable({ metrics, asOfDate }: PmsPerformanceTableProps) {
  if (!metrics || metrics.length === 0) return null;

  const hasBenchmark = metrics.some((m) => m.benchmark_return_pct != null);

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">
          Performance Summary
          {hasBenchmark && <span className="text-slate-400 font-normal ml-1"> — Portfolio vs NIFTY 50</span>}
        </h3>
        {asOfDate && (
          <span className="text-[11px] text-slate-400">as of {asOfDate}</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            {/* Group header */}
            {hasBenchmark && (
              <tr className="border-b border-slate-100">
                <th className="px-4 py-1.5" />
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-teal-600 uppercase tracking-wider">
                  Return
                </th>
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-teal-600 uppercase tracking-wider">
                  CAGR
                </th>
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Volatility
                </th>
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Max DD
                </th>
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Sharpe
                </th>
                <th colSpan={2} className="text-center px-2 py-1.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider">
                  Sortino
                </th>
              </tr>
            )}
            <tr className="border-b border-slate-100">
              <th className="text-left px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Period
              </th>
              {hasBenchmark ? (
                <>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
                  <th className="text-right px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
                </>
              ) : (
                <>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Return</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">CAGR</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Volatility</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Max DD</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Sharpe</th>
                  <th className="text-right px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">Sortino</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.period} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-4 py-2 font-medium text-slate-700 whitespace-nowrap">
                  {PERIOD_LABELS[m.period] || m.period}
                </td>
                {hasBenchmark ? (
                  <>
                    {/* Return */}
                    <td className={`px-2 py-2 text-right font-mono tabular-nums text-xs font-semibold ${colorPct(m.return_pct)}`}>
                      {fmtPct(m.return_pct)}
                    </td>
                    <td className={`px-2 py-2 text-right font-mono tabular-nums text-xs ${colorPct(m.benchmark_return_pct)}`}>
                      {fmtPct(m.benchmark_return_pct)}
                    </td>
                    {/* CAGR */}
                    <td className={`px-2 py-2 text-right font-mono tabular-nums text-xs font-semibold ${colorPct(m.cagr_pct)}`}>
                      {fmtPct(m.cagr_pct)}
                    </td>
                    <td className={`px-2 py-2 text-right font-mono tabular-nums text-xs ${colorPct(m.benchmark_cagr_pct)}`}>
                      {fmtPct(m.benchmark_cagr_pct)}
                    </td>
                    {/* Volatility */}
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-600">
                      {fmtPct(m.volatility_pct)}
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-400">
                      {fmtPct(m.benchmark_volatility_pct)}
                    </td>
                    {/* Max DD */}
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-red-600">
                      {m.max_drawdown_pct != null ? `${m.max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-red-400">
                      {m.benchmark_max_drawdown_pct != null ? `${m.benchmark_max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    {/* Sharpe */}
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-600">
                      {fmtRatio(m.sharpe_ratio)}
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-400">
                      {fmtRatio(m.benchmark_sharpe_ratio)}
                    </td>
                    {/* Sortino */}
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-600">
                      {fmtRatio(m.sortino_ratio)}
                    </td>
                    <td className="px-2 py-2 text-right font-mono tabular-nums text-xs text-slate-400">
                      {fmtRatio(m.benchmark_sortino_ratio)}
                    </td>
                  </>
                ) : (
                  <>
                    <td className={`px-3 py-2 text-right font-mono tabular-nums font-semibold ${colorPct(m.return_pct)}`}>
                      {fmtPct(m.return_pct)}
                    </td>
                    <td className={`px-3 py-2 text-right font-mono tabular-nums ${colorPct(m.cagr_pct)}`}>
                      {fmtPct(m.cagr_pct)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-600">
                      {fmtPct(m.volatility_pct)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-red-600">
                      {m.max_drawdown_pct != null ? `${m.max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-600">
                      {fmtRatio(m.sharpe_ratio)}
                    </td>
                    <td className="px-3 py-2 text-right font-mono tabular-nums text-slate-600">
                      {fmtRatio(m.sortino_ratio)}
                    </td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
