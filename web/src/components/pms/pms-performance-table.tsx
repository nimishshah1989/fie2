"use client";

import type { PmsMetric } from "@/lib/pms-types";

interface PmsPerformanceTableProps {
  metrics: PmsMetric[];
  asOfDate: string | null;
}

function formatVal(v: number | null, suffix: string = "%"): string {
  if (v == null) return "—";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(2)}${suffix}`;
}

function colorClass(v: number | null): string {
  if (v == null) return "text-slate-500";
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

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-5 py-3 border-b border-slate-100 flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-700">Performance Summary</h3>
        {asOfDate && (
          <span className="text-[11px] text-slate-400">as of {asOfDate}</span>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="text-left px-5 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Period
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Return
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                CAGR
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Volatility
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Max DD
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Sharpe
              </th>
              <th className="text-right px-4 py-2.5 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Sortino
              </th>
            </tr>
          </thead>
          <tbody>
            {metrics.map((m) => (
              <tr key={m.period} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="px-5 py-2.5 font-medium text-slate-700">
                  {PERIOD_LABELS[m.period] || m.period}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono tabular-nums font-semibold ${colorClass(m.return_pct)}`}>
                  {formatVal(m.return_pct)}
                </td>
                <td className={`px-4 py-2.5 text-right font-mono tabular-nums ${colorClass(m.cagr_pct)}`}>
                  {formatVal(m.cagr_pct)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-slate-600">
                  {formatVal(m.volatility_pct)}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-red-600">
                  {m.max_drawdown_pct != null ? `${m.max_drawdown_pct.toFixed(2)}%` : "—"}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-slate-600">
                  {m.sharpe_ratio != null ? m.sharpe_ratio.toFixed(2) : "—"}
                </td>
                <td className="px-4 py-2.5 text-right font-mono tabular-nums text-slate-600">
                  {m.sortino_ratio != null ? m.sortino_ratio.toFixed(2) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
