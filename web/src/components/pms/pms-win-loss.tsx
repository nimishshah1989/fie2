"use client";

import useSWR from "swr";
import { fetchPmsWinLoss } from "@/lib/pms-api";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPrice } from "@/lib/utils";

interface PmsWinLossProps {
  portfolioId: number;
  period?: string;
}

export function PmsWinLoss({ portfolioId, period }: PmsWinLossProps) {
  const periodParam = period && period !== "ALL" ? period : undefined;
  const { data: stats, isLoading } = useSWR(
    `pms-winloss-${portfolioId}-${period || "ALL"}`,
    () => fetchPmsWinLoss(portfolioId, periodParam),
    { refreshInterval: 300_000 }
  );

  if (isLoading) return <Skeleton className="h-48 rounded-xl" />;
  if (!stats || stats.total_scripts_traded === 0) return null;

  const kpis = [
    {
      label: "Win Rate",
      value: `${stats.win_rate_pct.toFixed(2)}%`,
      explanation: `${stats.winning_trades} profitable exits vs ${stats.losing_trades} loss-making exits out of ${stats.total_scripts_traded} total scripts traded. Calculated as winning trades / total trades with exits.`,
      color: stats.win_rate_pct >= 50 ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Profit Factor",
      value: stats.profit_factor != null ? stats.profit_factor.toFixed(2) : "N/A",
      explanation: stats.profit_factor != null
        ? `Ratio of total profits to total losses: ${formatPrice(stats.total_profit)} gained / ${formatPrice(Math.abs(stats.total_loss))} lost. Above 1.0 means profits exceed losses; above 2.0 is excellent.`
        : "Cannot compute — no losing trades recorded.",
      color: stats.profit_factor != null && stats.profit_factor >= 1 ? "text-emerald-600" : "text-red-600",
    },
    {
      label: "Avg Win",
      value: formatPrice(stats.avg_win),
      explanation: `Average profit per winning trade. Calculated as total realised profit / number of winning trades.`,
      color: "text-emerald-600",
    },
    {
      label: "Avg Loss",
      value: formatPrice(Math.abs(stats.avg_loss)),
      explanation: `Average loss per losing trade. Calculated as total realised loss / number of losing trades.`,
      color: "text-red-600",
    },
  ];

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-sm font-semibold text-slate-700 mb-4">
        Win/Loss Analysis
        <span className="text-slate-400 font-normal ml-1.5">
          ({stats.total_scripts_traded} scripts with exits)
        </span>
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
        {kpis.map((kpi) => (
          <div key={kpi.label} className="p-3 rounded-lg bg-slate-50">
            <p className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">{kpi.label}</p>
            <p className={`text-lg font-bold font-mono tabular-nums mt-0.5 ${kpi.color}`}>
              {kpi.value}
            </p>
            <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
              {kpi.explanation}
            </p>
          </div>
        ))}
      </div>

      {/* Summary bar */}
      <div className="flex items-center gap-2 text-xs">
        <div className="flex-1 flex items-center gap-2">
          <div className="h-2 rounded-full bg-emerald-500" style={{ width: `${stats.win_rate_pct}%` }} />
          <div className="h-2 rounded-full bg-red-400 flex-1" />
        </div>
        <span className="text-slate-500 whitespace-nowrap font-mono tabular-nums">
          {formatPrice(stats.total_profit)} profit / {formatPrice(Math.abs(stats.total_loss))} loss
        </span>
      </div>
    </div>
  );
}
