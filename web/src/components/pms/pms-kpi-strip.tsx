"use client";

import type { PmsSummary } from "@/lib/pms-types";
import { formatPct } from "@/lib/utils";

interface PmsKpiStripProps {
  summary: PmsSummary;
}

function formatRs(value: number | null): string {
  if (value == null) return "—";
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

function formatCrores(value: number | null): string {
  if (value == null) return "—";
  const cr = value / 1e7;
  return `₹${cr.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} Cr`;
}

export function PmsKpiStrip({ summary }: PmsKpiStripProps) {
  const kpis = [
    {
      label: "Current NAV",
      value: formatRs(summary.latest_nav),
      sub: summary.latest_unit_nav != null
        ? `TWR Index: ${summary.latest_unit_nav.toFixed(2)} | ${summary.latest_date}`
        : `as of ${summary.latest_date}`,
      color: "text-teal-600",
    },
    {
      label: "Corpus",
      value: formatCrores(summary.latest_corpus),
      sub: summary.latest_liquidity_pct != null
        ? `${summary.latest_liquidity_pct.toFixed(2)}% liquidity`
        : undefined,
      color: "text-slate-900",
    },
    {
      label: "CAGR (Since Inception)",
      value: summary.cagr_pct != null ? formatPct(summary.cagr_pct) : "—",
      sub: summary.return_pct != null ? `${formatPct(summary.return_pct)} absolute` : undefined,
      color: summary.cagr_pct != null && summary.cagr_pct >= 0
        ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Max Drawdown",
      value: summary.max_drawdown_pct != null
        ? `${summary.max_drawdown_pct.toFixed(2)}%` : "—",
      sub: summary.sharpe_ratio != null
        ? `Sharpe: ${summary.sharpe_ratio.toFixed(2)}` : undefined,
      color: "text-red-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {kpis.map((kpi) => (
        <div
          key={kpi.label}
          className="bg-white rounded-xl border border-slate-200 p-4"
        >
          <p className="text-xs text-slate-500 font-medium">{kpi.label}</p>
          <p className={`text-xl font-bold font-mono tabular-nums mt-1 ${kpi.color}`}>
            {kpi.value}
          </p>
          {kpi.sub && (
            <p className="text-[11px] text-slate-400 mt-0.5">{kpi.sub}</p>
          )}
        </div>
      ))}
    </div>
  );
}
