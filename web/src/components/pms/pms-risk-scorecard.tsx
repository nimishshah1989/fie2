"use client";

import useSWR from "swr";
import { fetchPmsRiskAnalytics } from "@/lib/pms-api";
import { Skeleton } from "@/components/ui/skeleton";

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
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
            {risk.up_capture_ratio != null && (
              <MetricCard
                label="Up Capture"
                value={`${risk.up_capture_ratio.toFixed(1)}%`}
                color={risk.up_capture_ratio >= 100 ? "text-emerald-600" : "text-slate-700"}
                explanation="Measures what % of the benchmark's gains the portfolio captures on up days. Above 100% means we gain more than the market when it rises."
              />
            )}
            {risk.down_capture_ratio != null && (
              <MetricCard
                label="Down Capture"
                value={`${risk.down_capture_ratio.toFixed(1)}%`}
                color={risk.down_capture_ratio <= 80 ? "text-emerald-600" : "text-red-600"}
                explanation="Measures what % of the benchmark's losses the portfolio takes on down days. Below 100% means we lose less than the market when it falls — a key sign of active risk management."
              />
            )}
            {risk.beta != null && (
              <MetricCard
                label="Beta"
                value={risk.beta.toFixed(2)}
                color={risk.beta <= 1 ? "text-emerald-600" : "text-amber-600"}
                explanation="Measures portfolio sensitivity to market movements. Beta < 1 means lower volatility than the market. Calculated as covariance(portfolio, benchmark) / variance(benchmark)."
              />
            )}
            {risk.information_ratio != null && (
              <MetricCard
                label="Information Ratio"
                value={risk.information_ratio.toFixed(2)}
                color={risk.information_ratio > 0 ? "text-emerald-600" : "text-red-600"}
                explanation="Measures risk-adjusted excess return over the benchmark. Calculated as annualised excess return / tracking error. Above 0.5 is considered good active management."
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
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <MetricCard
            label="Ulcer Index"
            value={risk.ulcer_index.toFixed(2)}
            color={risk.ulcer_index < 5 ? "text-emerald-600" : risk.ulcer_index < 10 ? "text-amber-600" : "text-red-600"}
            explanation="Measures the depth and duration of drawdowns. Unlike max drawdown which is a single point, Ulcer Index captures sustained pain. Calculated as RMS of all drawdown percentages. Lower is better."
          />
          <MetricCard
            label="Max Consecutive Loss"
            value={`${risk.max_consecutive_loss_months} months`}
            color={risk.max_consecutive_loss_months <= 3 ? "text-emerald-600" : "text-red-600"}
            explanation="The longest streak of consecutive negative monthly returns. Fewer consecutive losing months indicates better drawdown recovery and risk control."
          />
          {risk.avg_cash_pct != null && (
            <MetricCard
              label="Avg Cash Held"
              value={`${risk.avg_cash_pct.toFixed(1)}%`}
              color="text-amber-600"
              explanation={`Average cash + liquid fund allocation as a % of corpus across all days. Current allocation: ${risk.current_cash_pct?.toFixed(1) ?? 0}%. Higher cash during volatile markets shows tactical risk management.`}
            />
          )}
          {risk.max_cash_pct != null && (
            <MetricCard
              label="Max Cash Held"
              value={`${risk.max_cash_pct.toFixed(1)}%`}
              color="text-amber-600"
              explanation="Peak defensive positioning — the highest % of the portfolio held in cash and liquid funds on any single day. Shows willingness to go heavily defensive during market stress."
            />
          )}
        </div>
      </div>

      {/* Monthly Return Profile */}
      <div>
        <p className="text-[10px] text-slate-400 uppercase tracking-wide font-medium mb-2">
          Monthly Return Profile
        </p>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          <MetricCard
            label="Monthly Hit Rate"
            value={`${risk.hit_rate_monthly.toFixed(1)}%`}
            color={risk.hit_rate_monthly >= 60 ? "text-emerald-600" : "text-slate-700"}
            explanation={`Percentage of months with positive returns: ${risk.positive_months} profitable months out of ${risk.total_months} total. A hit rate above 60% is excellent for an actively managed portfolio.`}
          />
          <MetricCard
            label="Best Month"
            value={`+${risk.best_month_pct.toFixed(2)}%`}
            color="text-emerald-600"
            explanation={`The single best monthly return achieved. Average gain in positive months: +${risk.avg_positive_month_pct.toFixed(2)}%. Compares the upside potential to the downside risk.`}
          />
          <MetricCard
            label="Worst Month"
            value={`${risk.worst_month_pct.toFixed(2)}%`}
            color="text-red-600"
            explanation={`The single worst monthly return suffered. Average loss in negative months: ${risk.avg_negative_month_pct.toFixed(2)}%. The ratio of avg gain to avg loss shows asymmetric return quality.`}
          />
          {risk.correlation != null && (
            <MetricCard
              label="Market Correlation"
              value={risk.correlation.toFixed(2)}
              color={risk.correlation < 0.7 ? "text-emerald-600" : "text-slate-700"}
              explanation="Pearson correlation of daily returns with NIFTY 50. Below 0.7 means the portfolio has meaningful independent return sources. High correlation means returns closely track the market."
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
  label, value, color, explanation,
}: {
  label: string;
  value: string;
  color: string;
  explanation: string;
}) {
  return (
    <div className="p-3 rounded-lg bg-slate-50">
      <p className="text-[10px] text-slate-500 uppercase tracking-wide font-medium">
        {label}
      </p>
      <p className={`text-lg font-bold font-mono tabular-nums mt-0.5 ${color}`}>
        {value}
      </p>
      <p className="text-[10px] text-slate-400 mt-1.5 leading-relaxed">
        {explanation}
      </p>
    </div>
  );
}
