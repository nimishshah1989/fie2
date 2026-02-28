"use client";

import { StatsRow } from "@/components/stats-row";
import { formatPct } from "@/lib/utils";
import type { PortfolioPerformance } from "@/lib/portfolio-types";

// Format INR values (no decimals, Indian locale)
function fmtINR(v: number | null): string {
  if (v == null) return "—";
  return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

interface PortfolioKpiStripProps {
  performance: PortfolioPerformance;
}

export function PortfolioKpiStrip({ performance: p }: PortfolioKpiStripProps) {
  const stats = [
    {
      label: "Invested",
      value: fmtINR(p.total_invested),
    },
    {
      label: "Current Value",
      value: fmtINR(p.current_value),
    },
    {
      label: "Unrealized P&L",
      value: `${fmtINR(p.unrealized_pnl)} (${formatPct(p.unrealized_pnl_pct)})`,
      color: p.unrealized_pnl >= 0 ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Realized P&L",
      value: fmtINR(p.realized_pnl),
      color: p.realized_pnl >= 0 ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Total Return",
      value: formatPct(p.total_return_pct),
      color: p.total_return_pct >= 0 ? "text-emerald-600" : "text-red-600",
    },
    ...(p.xirr != null ? [{
      label: "XIRR",
      value: formatPct(p.xirr),
      color: p.xirr >= 0 ? "text-emerald-600" : "text-red-600",
    }] : []),
    ...(p.cagr != null ? [{
      label: "CAGR",
      value: formatPct(p.cagr),
      color: p.cagr >= 0 ? "text-emerald-600" : "text-red-600",
    }] : []),
    ...(p.max_drawdown != null ? [{
      label: "Max Drawdown",
      value: formatPct(p.max_drawdown),
      color: "text-red-600",
    }] : []),
    ...(p.alpha != null ? [{
      label: "Alpha",
      value: formatPct(p.alpha),
      color: p.alpha >= 0 ? "text-emerald-600" : "text-red-600",
    }] : []),
  ];

  return <StatsRow stats={stats} />;
}
