"use client";

import { useState } from "react";
import type { PmsMetric } from "@/lib/pms-types";
import { Info } from "lucide-react";

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

const METRIC_TOOLTIPS: Record<string, string> = {
  "Absolute Return":
    "Total percentage gain or loss over the period. Calculated as (End NAV − Start NAV) / Start NAV × 100.",
  "CAGR":
    "Compound Annual Growth Rate — the annualised return that smooths out volatility. Shows what constant annual rate would produce the same total return.",
  "Volatility":
    "Annualised standard deviation of daily returns. Higher volatility means larger day-to-day swings. Lower is generally better for risk-adjusted performance.",
  "Max DD":
    "Maximum Drawdown — the largest peak-to-trough decline during the period. Shows the worst loss an investor would have experienced.",
  "Sharpe":
    "Risk-adjusted return: (Portfolio Return − Risk-Free Rate) / Volatility. Above 1.0 is good, above 2.0 is excellent. Uses 6.5% as the risk-free rate (Indian T-bill proxy).",
  "Sortino":
    "Like Sharpe but only penalises downside volatility (bad risk). Ignores upside moves, making it more relevant for asymmetric return profiles. Higher is better.",
};

function InfoTooltip({ text }: { text: string }) {
  const [show, setShow] = useState(false);
  return (
    <span className="relative inline-block ml-1">
      <Info
        className="h-3 w-3 text-slate-300 hover:text-slate-500 cursor-help inline"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
      />
      {show && (
        <span className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-1.5 w-56 px-3 py-2 text-[10px] leading-relaxed text-slate-600 bg-white border border-slate-200 rounded-lg shadow-lg normal-case tracking-normal font-normal text-left">
          {text}
        </span>
      )}
    </span>
  );
}

export function PmsPerformanceTable({ metrics, asOfDate }: PmsPerformanceTableProps) {
  if (!metrics || metrics.length === 0) return null;

  const hasBenchmark = metrics.some((m) => m.benchmark_return_pct != null);

  const groupHeaders = [
    { label: "Absolute Return", accent: true },
    { label: "CAGR", accent: true },
    { label: "Volatility", accent: false },
    { label: "Max DD", accent: false },
    { label: "Sharpe", accent: false },
    { label: "Sortino", accent: false },
  ];

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
                {groupHeaders.map((gh) => (
                  <th
                    key={gh.label}
                    colSpan={2}
                    className={`text-center px-2 py-1.5 text-[10px] font-semibold uppercase tracking-wider ${
                      gh.accent ? "text-teal-600" : "text-slate-400"
                    }`}
                  >
                    {gh.label}
                    <InfoTooltip text={METRIC_TOOLTIPS[gh.label]} />
                  </th>
                ))}
              </tr>
            )}
            <tr className="border-b border-slate-100">
              <th className="text-left px-4 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Period
              </th>
              {hasBenchmark ? (
                <>
                  {groupHeaders.map((gh) => (
                    <PortBenchHeaders key={gh.label} />
                  ))}
                </>
              ) : (
                <>
                  {groupHeaders.map((gh) => (
                    <th key={gh.label} className="text-center px-3 py-2 text-xs font-semibold text-slate-400 uppercase tracking-wider">
                      {gh.label}
                      <InfoTooltip text={METRIC_TOOLTIPS[gh.label]} />
                    </th>
                  ))}
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
                    {/* Absolute Return */}
                    <td className={`px-2 py-2 text-center font-mono tabular-nums text-xs font-semibold ${colorPct(m.return_pct)}`}>
                      {fmtPct(m.return_pct)}
                    </td>
                    <td className={`px-2 py-2 text-center font-mono tabular-nums text-xs ${colorPct(m.benchmark_return_pct)}`}>
                      {fmtPct(m.benchmark_return_pct)}
                    </td>
                    {/* CAGR */}
                    <td className={`px-2 py-2 text-center font-mono tabular-nums text-xs font-semibold ${colorPct(m.cagr_pct)}`}>
                      {fmtPct(m.cagr_pct)}
                    </td>
                    <td className={`px-2 py-2 text-center font-mono tabular-nums text-xs ${colorPct(m.benchmark_cagr_pct)}`}>
                      {fmtPct(m.benchmark_cagr_pct)}
                    </td>
                    {/* Volatility */}
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-600">
                      {fmtPct(m.volatility_pct)}
                    </td>
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-400">
                      {fmtPct(m.benchmark_volatility_pct)}
                    </td>
                    {/* Max DD */}
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-red-600">
                      {m.max_drawdown_pct != null ? `${m.max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-red-400">
                      {m.benchmark_max_drawdown_pct != null ? `${m.benchmark_max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    {/* Sharpe */}
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-600">
                      {fmtRatio(m.sharpe_ratio)}
                    </td>
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-400">
                      {fmtRatio(m.benchmark_sharpe_ratio)}
                    </td>
                    {/* Sortino */}
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-600">
                      {fmtRatio(m.sortino_ratio)}
                    </td>
                    <td className="px-2 py-2 text-center font-mono tabular-nums text-xs text-slate-400">
                      {fmtRatio(m.benchmark_sortino_ratio)}
                    </td>
                  </>
                ) : (
                  <>
                    <td className={`px-3 py-2 text-center font-mono tabular-nums font-semibold ${colorPct(m.return_pct)}`}>
                      {fmtPct(m.return_pct)}
                    </td>
                    <td className={`px-3 py-2 text-center font-mono tabular-nums ${colorPct(m.cagr_pct)}`}>
                      {fmtPct(m.cagr_pct)}
                    </td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-600">
                      {fmtPct(m.volatility_pct)}
                    </td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-red-600">
                      {m.max_drawdown_pct != null ? `${m.max_drawdown_pct.toFixed(2)}%` : "—"}
                    </td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-600">
                      {fmtRatio(m.sharpe_ratio)}
                    </td>
                    <td className="px-3 py-2 text-center font-mono tabular-nums text-slate-600">
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

function PortBenchHeaders() {
  return (
    <>
      <th className="text-center px-2 py-2 text-[10px] font-medium text-teal-600">Port</th>
      <th className="text-center px-2 py-2 text-[10px] font-medium text-slate-400">Bench</th>
    </>
  );
}
