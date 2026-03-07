"use client";

import useSWR from "swr";
import { fetchPmsRiskAnalytics } from "@/lib/pms-api";
import { Skeleton } from "@/components/ui/skeleton";
import { formatPct } from "@/lib/utils";

interface PmsRiskScorecardProps {
  portfolioId: number;
}

export function PmsRiskScorecard({ portfolioId }: PmsRiskScorecardProps) {
  const { data: risk, isLoading } = useSWR(
    `pms-risk-${portfolioId}`,
    () => fetchPmsRiskAnalytics(portfolioId),
    { refreshInterval: 300_000 }
  );

  if (isLoading) return <Skeleton className="h-64 rounded-xl" />;
  if (!risk) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-5">
      <h3 className="text-sm font-semibold text-slate-700">
        Risk Management Scorecard
      </h3>

      {/* Benchmark Comparison */}
      {(risk.up_capture_ratio != null || risk.beta != null) && (
        <div>
          <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium mb-2">
            vs NIFTY 50
          </p>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            {risk.up_capture_ratio != null && (
              <MetricCard
                label="Up Capture"
                value={`${risk.up_capture_ratio}%`}
                sub="% of benchmark gains captured"
                color={risk.up_capture_ratio >= 100 ? "text-emerald-600" : "text-slate-700"}
              />
            )}
            {risk.down_capture_ratio != null && (
              <MetricCard
                label="Down Capture"
                value={`${risk.down_capture_ratio}%`}
                sub="% of benchmark losses taken"
                color={risk.down_capture_ratio <= 80 ? "text-emerald-600" : "text-red-600"}
              />
            )}
            {risk.beta != null && (
              <MetricCard
                label="Beta"
                value={risk.beta.toFixed(2)}
                sub={risk.beta < 1 ? "Lower risk than market" : "Higher risk than market"}
                color={risk.beta <= 1 ? "text-emerald-600" : "text-amber-600"}
              />
            )}
            {risk.information_ratio != null && (
              <MetricCard
                label="Information Ratio"
                value={risk.information_ratio.toFixed(2)}
                sub="Risk-adjusted active return"
                color={risk.information_ratio > 0 ? "text-emerald-600" : "text-red-600"}
              />
            )}
          </div>
        </div>
      )}

      {/* Drawdown & Stress */}
      <div>
        <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium mb-2">
          Drawdown & Stress Management
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard
            label="Ulcer Index"
            value={risk.ulcer_index.toFixed(2)}
            sub="Pain of drawdowns (lower = better)"
            color={risk.ulcer_index < 5 ? "text-emerald-600" : risk.ulcer_index < 10 ? "text-amber-600" : "text-red-600"}
          />
          <MetricCard
            label="Max Consecutive Loss"
            value={`${risk.max_consecutive_loss_months} months`}
            sub="Longest losing streak"
            color={risk.max_consecutive_loss_months <= 3 ? "text-emerald-600" : "text-red-600"}
          />
          {risk.avg_cash_pct != null && (
            <MetricCard
              label="Avg Cash Held"
              value={`${risk.avg_cash_pct}%`}
              sub={`Current: ${risk.current_cash_pct ?? 0}%`}
              color="text-amber-600"
            />
          )}
          {risk.max_cash_pct != null && (
            <MetricCard
              label="Max Cash Held"
              value={`${risk.max_cash_pct}%`}
              sub="Peak defensive positioning"
              color="text-amber-600"
            />
          )}
        </div>
      </div>

      {/* Monthly Return Profile */}
      <div>
        <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium mb-2">
          Monthly Return Profile
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          <MetricCard
            label="Hit Rate"
            value={`${risk.hit_rate_monthly}%`}
            sub={`${risk.positive_months} up / ${risk.negative_months} down of ${risk.total_months} months`}
            color={risk.hit_rate_monthly >= 60 ? "text-emerald-600" : "text-slate-700"}
          />
          <MetricCard
            label="Best Month"
            value={formatPct(risk.best_month_pct)}
            sub={`Avg gain: ${formatPct(risk.avg_positive_month_pct)}`}
            color="text-emerald-600"
          />
          <MetricCard
            label="Worst Month"
            value={formatPct(risk.worst_month_pct)}
            sub={`Avg loss: ${formatPct(risk.avg_negative_month_pct)}`}
            color="text-red-600"
          />
          {risk.correlation != null && (
            <MetricCard
              label="Market Correlation"
              value={risk.correlation.toFixed(2)}
              sub={risk.correlation < 0.7 ? "Low market dependence" : "Moves with market"}
              color={risk.correlation < 0.7 ? "text-emerald-600" : "text-slate-700"}
            />
          )}
        </div>

        {/* Visual bar: positive vs negative months */}
        <div className="flex items-center gap-2 mt-3 text-xs">
          <div className="flex-1 flex items-center gap-1">
            <div
              className="h-2.5 rounded-full bg-emerald-500"
              style={{ width: `${risk.hit_rate_monthly}%` }}
            />
            <div className="h-2.5 rounded-full bg-red-400 flex-1" />
          </div>
          <span className="text-slate-500 whitespace-nowrap font-mono tabular-nums">
            {risk.positive_months}W / {risk.negative_months}L
          </span>
        </div>
      </div>
    </div>
  );
}

function MetricCard({
  label, value, sub, color,
}: {
  label: string;
  value: string;
  sub?: string;
  color: string;
}) {
  return (
    <div className="p-3 rounded-lg bg-slate-50">
      <p className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">
        {label}
      </p>
      <p className={`text-lg font-bold font-mono tabular-nums mt-0.5 ${color}`}>
        {value}
      </p>
      {sub && (
        <p className="text-[10px] text-slate-400 mt-0.5">{sub}</p>
      )}
    </div>
  );
}
