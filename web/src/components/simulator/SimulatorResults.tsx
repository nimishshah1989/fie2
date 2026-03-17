"use client";

import type { SimulationResult } from "@/lib/simulator-types";
import { cn } from "@/lib/utils";

interface Props {
  result: SimulationResult;
}

function fmtINR(v: number): string {
  return "₹" + Math.abs(v).toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
}

function Stat({ label, value, sub, color }: { label: string; value: string; sub?: string; color?: string }) {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4">
      <p className="text-xs text-slate-400 mb-1">{label}</p>
      <p className={cn("text-xl font-bold font-mono tabular-nums", color || "text-slate-800")}>{value}</p>
      {sub && <p className="text-[11px] text-slate-400 mt-0.5">{sub}</p>}
    </div>
  );
}

export function SimulatorResults({ result }: Props) {
  const regReturn = result.reg_value - result.reg_invested;
  const enhReturn = result.enh_value - result.enh_invested;
  const regPct = (regReturn / result.reg_invested) * 100;
  const enhPct = (enhReturn / result.enh_invested) * 100;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h3 className="text-lg font-bold text-slate-800">{result.fund_name}</h3>
          <p className="text-xs text-slate-500">
            {result.num_triggers} top-ups out of {result.total_sips} SIPs
            {result.cooloff_skips > 0 && ` · ${result.cooloff_skips} skipped (cool-off)`}
          </p>
        </div>
        <div className={cn(
          "px-3 py-1.5 rounded-full text-sm font-bold font-mono",
          result.alpha_pct > 0 ? "bg-emerald-100 text-emerald-700" : "bg-red-100 text-red-700"
        )}>
          Alpha: {result.alpha_pct > 0 ? "+" : ""}{result.alpha_pct.toFixed(2)}%
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-blue-500" />
            <span className="text-sm font-semibold text-slate-700">Regular SIP</span>
          </div>
          <Stat label="Total Invested" value={fmtINR(result.reg_invested)} />
          <Stat
            label="Current Value"
            value={fmtINR(result.reg_value)}
            sub={`${regPct >= 0 ? "+" : ""}${regPct.toFixed(1)}% absolute`}
            color={regReturn >= 0 ? "text-emerald-600" : "text-red-600"}
          />
          <Stat
            label="XIRR"
            value={result.reg_xirr != null ? `${result.reg_xirr.toFixed(2)}%` : "—"}
            color={result.reg_xirr && result.reg_xirr > 0 ? "text-emerald-600" : "text-red-600"}
          />
        </div>

        <div className="space-y-3">
          <div className="flex items-center gap-2 mb-1">
            <div className="w-3 h-3 rounded-full bg-teal-500" />
            <span className="text-sm font-semibold text-slate-700">Enhanced SIP</span>
          </div>
          <Stat label="Total Invested" value={fmtINR(result.enh_invested)} />
          <Stat
            label="Current Value"
            value={fmtINR(result.enh_value)}
            sub={`${enhPct >= 0 ? "+" : ""}${enhPct.toFixed(1)}% absolute`}
            color={enhReturn >= 0 ? "text-emerald-600" : "text-red-600"}
          />
          <Stat
            label="XIRR"
            value={result.enh_xirr != null ? `${result.enh_xirr.toFixed(2)}%` : "—"}
            color={result.enh_xirr && result.enh_xirr > 0 ? "text-emerald-600" : "text-red-600"}
          />
        </div>
      </div>

      <div className="bg-gradient-to-r from-teal-50 to-emerald-50 rounded-xl border border-teal-200 p-4">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-xs text-teal-600 mb-1">Extra Invested</p>
            <p className="text-lg font-bold font-mono text-teal-700">{fmtINR(result.extra_invested)}</p>
          </div>
          <div>
            <p className="text-xs text-teal-600 mb-1">Alpha (Value)</p>
            <p className={cn("text-lg font-bold font-mono", result.alpha_value >= 0 ? "text-emerald-700" : "text-red-700")}>
              {result.alpha_value >= 0 ? "+" : "-"}{fmtINR(result.alpha_value)}
            </p>
          </div>
          <div>
            <p className="text-xs text-teal-600 mb-1">Trigger Rate</p>
            <p className="text-lg font-bold font-mono text-teal-700">
              {result.total_sips > 0 ? ((result.num_triggers / result.total_sips) * 100).toFixed(0) : 0}%
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
