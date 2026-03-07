"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, BookOpen } from "lucide-react";

const SECTIONS = [
  {
    title: "Time-Weighted Return (TWR)",
    content: `Raw portfolio NAV is distorted by capital inflows and outflows — a ₹10L deposit makes NAV jump even if markets are flat. TWR eliminates this by computing a "unit NAV" index (starting at 100 on inception date).

**How it works:**
- Each day, the system detects capital flows from corpus changes (corpus_today − corpus_yesterday)
- The daily return is: curr_NAV / (prev_NAV + cash_flow)
- This neutralizes the effect of deposits and withdrawals
- The unit NAV index is chain-multiplied: unit_nav_today = unit_nav_yesterday × daily_return

**All metrics (CAGR, Sharpe, drawdowns) are computed from this TWR-adjusted unit NAV, not the raw NAV.**`,
  },
  {
    title: "CAGR (Compound Annual Growth Rate)",
    content: `Annualized return that smooths out volatility over the holding period.

**Formula:** CAGR = (End_NAV / Start_NAV)^(1/years) − 1

Where years = calendar days / 365.25. Uses TWR unit NAV values.`,
  },
  {
    title: "Annualized Volatility",
    content: `Measures the dispersion of daily returns, scaled to annual frequency.

**Formula:** Volatility = StdDev(daily_returns) × √252

Where 252 = trading days per year (Indian markets). Higher volatility means more unpredictable returns.`,
  },
  {
    title: "Maximum Drawdown",
    content: `The largest peak-to-trough decline in the TWR unit NAV over the entire period.

**Formula:** Max DD = min((NAV − running_max) / running_max)

A drawdown of −18% means the portfolio fell 18% from its highest point before recovering. Drawdown events with ≥2% decline are individually tracked with peak date, trough date, recovery date, and duration.`,
  },
  {
    title: "Sharpe Ratio",
    content: `Risk-adjusted return — how much excess return you get per unit of risk.

**Formula:** Sharpe = (Mean_daily_excess_return / StdDev_daily_excess_return) × √252

**Risk-free rate: 7% per annum** (RBI benchmark for Indian markets). A Sharpe above 1.0 is considered good; above 2.0 is excellent.`,
  },
  {
    title: "Sortino Ratio",
    content: `Like Sharpe, but only penalizes downside volatility — upside volatility is desirable.

**Formula:** Sortino = (Mean_daily_return − daily_rf) / downside_deviation × √252

Downside deviation = √(mean of squared negative excess returns). A higher Sortino means better risk-adjusted returns with less downside risk.`,
  },
  {
    title: "Calmar Ratio",
    content: `CAGR divided by maximum drawdown — measures return relative to worst-case loss.

**Formula:** Calmar = CAGR% / |Max Drawdown%|

A Calmar above 1.0 means the annualized return exceeds the worst drawdown.`,
  },
  {
    title: "Period Metrics",
    content: `All metrics are computed for multiple lookback periods using the most recent N trading days:

| Period | Trading Days |
|--------|-------------|
| 1M | 21 |
| 3M | 63 |
| 6M | 126 |
| 1Y | 252 |
| 3Y | 756 |
| 5Y | 1,260 |
| SI | All data (since inception) |

Metrics are recomputed on each data upload.`,
  },
  {
    title: "Data Source",
    content: `NAV data is sourced from PMS broker Excel reports containing daily corpus, equity holdings, ETF investments, bank balance, and net asset value. Each portfolio is identified by a UCC (Unique Client Code).

The system supports incremental uploads — existing dates are skipped, and only new data points are added. Metrics and drawdown events are fully recomputed after each upload.`,
  },
];

export function PmsMethodology() {
  const [expandedIdx, setExpandedIdx] = useState<number | null>(null);
  const [showAll, setShowAll] = useState(false);

  const toggle = (idx: number) => {
    setExpandedIdx(expandedIdx === idx ? null : idx);
  };

  if (!showAll) {
    return (
      <button
        onClick={() => setShowAll(true)}
        className="flex items-center gap-2 text-sm text-slate-500 hover:text-teal-600 transition-colors mt-2"
      >
        <BookOpen className="h-4 w-4" />
        <span>View calculation methodology</span>
      </button>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <BookOpen className="h-4 w-4 text-teal-600" />
          <h3 className="text-sm font-semibold text-slate-700">
            Calculation Methodology
          </h3>
        </div>
        <button
          onClick={() => setShowAll(false)}
          className="text-xs text-slate-400 hover:text-slate-600"
        >
          Hide
        </button>
      </div>

      <div className="space-y-1">
        {SECTIONS.map((section, idx) => (
          <div key={section.title} className="border-b border-slate-100 last:border-0">
            <button
              onClick={() => toggle(idx)}
              className="w-full flex items-center gap-2 py-2.5 text-left hover:bg-slate-50 rounded px-2 -mx-2 transition-colors"
            >
              {expandedIdx === idx ? (
                <ChevronDown className="h-3.5 w-3.5 text-teal-600 shrink-0" />
              ) : (
                <ChevronRight className="h-3.5 w-3.5 text-slate-400 shrink-0" />
              )}
              <span className="text-sm font-medium text-slate-700">
                {section.title}
              </span>
            </button>
            {expandedIdx === idx && (
              <div className="pl-6 pr-2 pb-3">
                <div className="text-xs text-slate-600 leading-relaxed whitespace-pre-line">
                  {section.content.split(/(\*\*.*?\*\*)/g).map((part, i) => {
                    if (part.startsWith("**") && part.endsWith("**")) {
                      return (
                        <span key={i} className="font-semibold text-slate-800">
                          {part.slice(2, -2)}
                        </span>
                      );
                    }
                    return <span key={i}>{part}</span>;
                  })}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
