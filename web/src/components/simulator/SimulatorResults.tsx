"use client";

import type { SimulationResult } from "@/lib/simulator-types";
import { cn } from "@/lib/utils";

interface Props {
  result: SimulationResult;
}

function formatINR(v: number): string {
  return "₹" + v.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function StatCard({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={cn("text-xl font-bold font-mono tabular-nums", color || "text-slate-800")}>{value}</p>
      {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function SimulatorResults({ result }: Props) {
  const regReturn = result.regular_current_value - result.regular_total_invested;
  const enhReturn = result.enhanced_current_value - result.enhanced_total_invested;
  const regReturnPct = (regReturn / result.regular_total_invested) * 100;
  const enhReturnPct = (enhReturn / result.enhanced_total_invested) * 100;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-lg font-bold text-slate-800">{result.fund_name}</h3>
          <p className="text-xs text-slate-500">
            Trigger: {result.metric_label} &middot; {result.num_triggers} triggers out of {result.total_sip_count} SIPs
          </p>
        </div>
        <div className={cn(
          "px-3 py-1.5 rounded-full text-sm font-bold font-mono",
          result.alpha_pct > 0 ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
        )}>
          Alpha: {result.alpha_pct > 0 ? "+" : ""}{result.alpha_pct.toFixed(2)}%
        </div>
      </div>

      {/* Comparison Grid */}
      <div className="grid grid-cols-2 gap-4">
        {/* Regular SIP Column */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-sm font-semibold text-slate-700">Regular SIP</span>
          </div>
          <StatCard label="Total Invested" value={formatINR(result.regular_total_invested)} />
          <StatCard
            label="Current Value"
            value={formatINR(result.regular_current_value)}
            sub={`${regReturnPct >= 0 ? "+" : ""}${regReturnPct.toFixed(1)}% absolute`}
            color={regReturn >= 0 ? "text-emerald-600" : "text-red-600"}
          />
          <StatCard label="Units" value={result.regular_units.toFixed(2)} />
          <StatCard
            label="XIRR"
            value={result.regular_xirr != null ? `${result.regular_xirr.toFixed(2)}%` : "—"}
            color={result.regular_xirr && result.regular_xirr > 0 ? "text-emerald-600" : "text-red-600"}
          />
        </div>

        {/* Enhanced SIP Column */}
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-teal-500" />
            <span className="text-sm font-semibold text-slate-700">Enhanced SIP</span>
          </div>
          <StatCard label="Total Invested" value={formatINR(result.enhanced_total_invested)} />
          <StatCard
            label="Current Value"
            value={formatINR(result.enhanced_current_value)}
            sub={`${enhReturnPct >= 0 ? "+" : ""}${enhReturnPct.toFixed(1)}% absolute`}
            color={enhReturn >= 0 ? "text-emerald-600" : "text-red-600"}
          />
          <StatCard label="Units" value={result.enhanced_units.toFixed(2)} />
          <StatCard
            label="XIRR"
            value={result.enhanced_xirr != null ? `${result.enhanced_xirr.toFixed(2)}%` : "—"}
            color={result.enhanced_xirr && result.enhanced_xirr > 0 ? "text-emerald-600" : "text-red-600"}
          />
        </div>
      </div>

      {/* Alpha Summary */}
      <div className="bg-gradient-to-r from-teal-50 to-emerald-50 rounded-xl border border-teal-200 p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-teal-600 mb-1">Extra Invested</p>
            <p className="text-lg font-bold font-mono text-teal-700">{formatINR(result.extra_invested)}</p>
          </div>
          <div>
            <p className="text-xs text-teal-600 mb-1">Alpha (Value)</p>
            <p className={cn("text-lg font-bold font-mono", result.alpha_value >= 0 ? "text-emerald-700" : "text-red-700")}>
              {result.alpha_value >= 0 ? "+" : ""}{formatINR(Math.abs(result.alpha_value))}
            </p>
          </div>
          <div>
            <p className="text-xs text-teal-600 mb-1">Trigger Rate</p>
            <p className="text-lg font-bold font-mono text-teal-700">
              {result.total_sip_count > 0 ? ((result.num_triggers / result.total_sip_count) * 100).toFixed(0) : 0}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
