"use client";

import { useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { useModelPortfolio, useModelTrades, useModelNAV, useModelPerformance } from "@/hooks/use-compass";
import { Skeleton } from "@/components/ui/skeleton";
import type { PortfolioType } from "@/lib/compass-types";

const PORTFOLIO_TABS: { key: PortfolioType; label: string; desc: string }[] = [
  { key: "etf_only", label: "ETF Only", desc: "Sector ETFs — liquid, low cost" },
  { key: "stock_etf", label: "Stock + ETF", desc: "Top stocks + sector ETFs blend" },
  { key: "stock_only", label: "Stock Only", desc: "Constituent stocks from leading sectors" },
];

function formatINR(v: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(v);
}

export function ModelPortfolioDashboard() {
  const [activeType, setActiveType] = useState<PortfolioType>("etf_only");

  const { portfolio, isLoading: loadingPortfolio } = useModelPortfolio(activeType);
  const { trades, isLoading: loadingTrades } = useModelTrades(activeType, 20);
  const { navHistory, isLoading: loadingNav } = useModelNAV(activeType, 365);
  const { performance, isLoading: loadingPerf } = useModelPerformance(activeType);

  if (loadingPortfolio || loadingPerf) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-10 w-full rounded-lg" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </div>
    );
  }

  const hasData = performance && performance.total_trades > 0;

  return (
    <div className="space-y-4">
      {/* Portfolio type selector */}
      <div className="flex items-center gap-1 bg-slate-100 rounded-lg p-1 w-fit">
        {PORTFOLIO_TABS.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveType(tab.key)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              activeType === tab.key
                ? "bg-white text-slate-900 shadow-sm"
                : "text-slate-500 hover:text-slate-700"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <p className="text-xs text-slate-400 -mt-2">
        {PORTFOLIO_TABS.find((t) => t.key === activeType)?.desc}
      </p>

      {/* Performance stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
        <StatCard label="NAV" value={performance?.current_nav?.toFixed(2) ?? "100.00"} />
        <StatCard
          label="Return"
          value={`${performance?.total_return_pct?.toFixed(2) ?? "0"}%`}
          positive={performance ? performance.total_return_pct > 0 : undefined}
        />
        <StatCard
          label="Alpha vs NIFTY"
          value={`${performance?.alpha_vs_nifty?.toFixed(2) ?? "0"}%`}
          positive={performance ? performance.alpha_vs_nifty > 0 : undefined}
        />
        <StatCard
          label="Alpha vs FM"
          value={performance?.alpha_vs_fm != null ? `${performance.alpha_vs_fm.toFixed(2)}%` : "—"}
          positive={performance?.alpha_vs_fm != null ? performance.alpha_vs_fm > 0 : undefined}
        />
        <StatCard label="Max Drawdown" value={`-${performance?.max_drawdown_pct?.toFixed(1) ?? "0"}%`} positive={false} />
        <StatCard label="Win Rate" value={`${performance?.win_rate_pct?.toFixed(0) ?? "0"}%`} />
        <StatCard label="Tax Paid" value={performance?.total_tax_paid ? formatINR(performance.total_tax_paid) : "₹0"} />
      </div>

      {/* NAV Chart */}
      {navHistory.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 p-4">
          <h3 className="text-sm font-semibold text-slate-900 mb-3">NAV: Model vs NIFTY vs FM Portfolio</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={navHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="date" tick={{ fontSize: 10, fill: "#94a3b8" }} tickFormatter={(d: string) => d.slice(5)} />
              <YAxis tick={{ fontSize: 11, fill: "#94a3b8" }} domain={["auto", "auto"]} />
              <Tooltip
                contentStyle={{ fontSize: 12, borderRadius: 8 }}
                formatter={(val: number, name: string) => [val.toFixed(2), name]}
              />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Line type="monotone" dataKey="nav" name="Model" stroke="#0d9488" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="benchmark_nav" name="NIFTY" stroke="#94a3b8" strokeWidth={1.5} dot={false} strokeDasharray="4 4" />
              <Line type="monotone" dataKey="fm_nav" name="FM Portfolio" stroke="#6366f1" strokeWidth={1.5} dot={false} strokeDasharray="2 2" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Current positions */}
      <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-100">
          <h3 className="text-sm font-semibold text-slate-900">
            Current Positions ({portfolio?.num_open ?? 0}/{portfolio?.max_positions ?? 6})
          </h3>
        </div>
        {portfolio?.positions && portfolio.positions.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-slate-50 border-b border-slate-100">
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-4 py-2">Sector</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Via</th>
                  <th className="text-left text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Entry</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Wt%</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">P&L</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Stop</th>
                  <th className="text-right text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Trail</th>
                  <th className="text-center text-xs font-semibold text-slate-400 uppercase tracking-wider px-3 py-2">Tax</th>
                </tr>
              </thead>
              <tbody>
                {portfolio.positions.map((p) => (
                  <tr key={p.instrument_id} className="border-b border-slate-50">
                    <td className="px-4 py-2.5">
                      <p className="font-medium text-slate-900">{p.sector_name}</p>
                      <p className="text-xs text-slate-400">{p.holding_days}d held</p>
                    </td>
                    <td className="px-3 py-2.5 text-slate-600 text-xs">{p.instrument_id}</td>
                    <td className="px-3 py-2.5 text-slate-500 text-xs">{p.entry_date}</td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-600">{p.weight_pct?.toFixed(1)}%</td>
                    <td className={`px-3 py-2.5 text-right font-mono font-medium ${(p.pnl_pct ?? 0) >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                      {p.pnl_pct != null ? `${p.pnl_pct > 0 ? "+" : ""}${p.pnl_pct.toFixed(1)}%` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-500">
                      {p.stop_loss ? `₹${p.stop_loss.toFixed(0)}` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-right font-mono text-slate-500">
                      {p.trailing_stop ? `₹${p.trailing_stop.toFixed(0)}` : "—"}
                    </td>
                    <td className="px-3 py-2.5 text-center">
                      <span className={`text-xs font-medium px-1.5 py-0.5 rounded ${
                        p.tax_type === "LTCG" ? "bg-emerald-50 text-emerald-600" : "bg-amber-50 text-amber-600"
                      }`}>
                        {p.tax_type ?? "—"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="p-8 text-center text-sm text-slate-400">
            No open positions. Model portfolio will start trading when sectors show BUY signals.
          </div>
        )}
      </div>

      {/* Recent trades */}
      {trades.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100">
            <h3 className="text-sm font-semibold text-slate-900">Recent Trades</h3>
          </div>
          <div className="divide-y divide-slate-50">
            {trades.slice(0, 10).map((t, i) => (
              <div key={i} className="flex items-center gap-3 px-4 py-2.5 text-sm">
                <span className="text-xs text-slate-400 w-20 shrink-0">{t.trade_date}</span>
                <span className={`text-xs font-semibold px-2 py-0.5 rounded ${t.side === "BUY" ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"}`}>
                  {t.side}
                </span>
                <span className="font-medium text-slate-900">{t.sector_name}</span>
                <span className="text-slate-500 text-xs">({t.instrument_id})</span>
                {t.pnl_pct != null && (
                  <span className={`text-xs font-mono font-medium ${t.pnl_pct >= 0 ? "text-emerald-600" : "text-red-600"}`}>
                    {t.pnl_pct > 0 ? "+" : ""}{t.pnl_pct.toFixed(1)}%
                  </span>
                )}
                {t.tax_impact != null && t.tax_impact > 0 && (
                  <span className="text-xs text-amber-500">tax: ₹{t.tax_impact.toFixed(0)}</span>
                )}
                <span className="ml-auto text-xs text-slate-400">{t.reason}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {!hasData && (
        <div className="bg-slate-50 rounded-xl border border-dashed border-slate-300 p-8 text-center">
          <p className="text-sm text-slate-500">Model portfolio has no trade history yet.</p>
          <p className="text-xs text-slate-400 mt-1">Use the Refresh button to compute RS scores and trigger the first rebalance cycle.</p>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, positive }: { label: string; value: string; positive?: boolean }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-500">{label}</p>
      <p className={`text-lg font-bold font-mono mt-1 ${
        positive === true ? "text-emerald-600" :
        positive === false ? "text-red-600" :
        "text-teal-600"
      }`}>
        {value}
      </p>
    </div>
  );
}
