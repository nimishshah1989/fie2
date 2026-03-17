"use client";

import { cn } from "@/lib/utils";
import type { BatchRow, Strategy } from "@/lib/simulator-types";

interface Props {
  strategy: Strategy;
  rows: BatchRow[];
  onFundClick: (fundCode: string) => void;
  selectedFund: string | null;
}

const PERIODS = ["1Y", "2Y", "3Y", "Lifetime"] as const;

function fmtINR(v: number): string {
  if (Math.abs(v) >= 1e7) return `₹${(v / 1e7).toFixed(1)}Cr`;
  if (Math.abs(v) >= 1e5) return `₹${(v / 1e5).toFixed(1)}L`;
  if (Math.abs(v) >= 1e3) return `₹${(v / 1e3).toFixed(1)}K`;
  return `₹${v.toFixed(0)}`;
}

function fmtPct(v: number | null): string {
  if (v === null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

export function StrategyTable({ strategy, rows, onFundClick, selectedFund }: Props) {
  // Group rows by fund
  const fundMap = new Map<string, { name: string; category: string; periods: Map<string, BatchRow> }>();
  for (const r of rows) {
    if (!fundMap.has(r.fund_code)) {
      fundMap.set(r.fund_code, { name: r.fund_name, category: r.category, periods: new Map() });
    }
    fundMap.get(r.fund_code)!.periods.set(r.period_label, r);
  }

  const funds = Array.from(fundMap.entries());

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="p-4 border-b border-slate-100">
        <h3 className="text-sm font-bold text-slate-800">{strategy.label}</h3>
        <p className="text-xs text-slate-500 mt-0.5">{strategy.description}</p>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50">
              <th className="text-left px-3 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider sticky left-0 bg-slate-50 min-w-[180px]">
                Fund
              </th>
              <th className="px-2 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-center">
                Cat
              </th>
              {PERIODS.map((p) => (
                <th key={`abs-${p}`} colSpan={1} className="px-2 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-right">
                  {p} Alpha
                </th>
              ))}
              {PERIODS.map((p) => (
                <th key={`xirr-${p}`} colSpan={1} className="px-2 py-2.5 text-[10px] font-semibold text-teal-500 uppercase tracking-wider text-right">
                  {p} ΔXIRR
                </th>
              ))}
              <th className="px-2 py-2.5 text-[10px] font-semibold text-slate-400 uppercase tracking-wider text-right">
                Triggers
              </th>
            </tr>
          </thead>
          <tbody>
            {funds.map(([code, fund]) => {
              const isSelected = selectedFund === code;
              // Use lifetime for trigger count
              const ltRow = fund.periods.get("Lifetime");

              return (
                <tr
                  key={code}
                  onClick={() => onFundClick(code)}
                  className={cn(
                    "border-b border-slate-50 cursor-pointer transition-colors",
                    isSelected
                      ? "bg-teal-50 hover:bg-teal-100"
                      : "hover:bg-slate-50"
                  )}
                >
                  <td className={cn(
                    "px-3 py-2.5 font-medium text-slate-700 sticky left-0 truncate max-w-[220px]",
                    isSelected ? "bg-teal-50" : "bg-white"
                  )}>
                    {fund.name.replace(" - Direct Growth", "")}
                  </td>
                  <td className="px-2 py-2.5 text-center">
                    <span className="bg-slate-100 text-slate-500 rounded px-1.5 py-0.5 text-[10px] font-medium">
                      {fund.category}
                    </span>
                  </td>
                  {PERIODS.map((p) => {
                    const r = fund.periods.get(p);
                    const val = r?.incremental_return_pct ?? null;
                    return (
                      <td key={`abs-${p}`} className="px-2 py-2.5 text-right font-mono tabular-nums">
                        <span className={cn(
                          "font-medium",
                          val === null ? "text-slate-300" : val > 0 ? "text-emerald-600" : "text-red-500"
                        )}>
                          {fmtPct(val)}
                        </span>
                      </td>
                    );
                  })}
                  {PERIODS.map((p) => {
                    const r = fund.periods.get(p);
                    const val = r?.incremental_xirr ?? null;
                    return (
                      <td key={`xirr-${p}`} className="px-2 py-2.5 text-right font-mono tabular-nums">
                        <span className={cn(
                          "font-medium",
                          val === null ? "text-slate-300" : val > 0 ? "text-teal-600" : "text-red-500"
                        )}>
                          {fmtPct(val)}
                        </span>
                      </td>
                    );
                  })}
                  <td className="px-2 py-2.5 text-right font-mono tabular-nums text-slate-500">
                    {ltRow ? `${ltRow.num_triggers}/${ltRow.total_sips}` : "—"}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {funds.length === 0 && (
        <div className="flex items-center justify-center py-12 text-sm text-slate-400">
          Loading strategy results...
        </div>
      )}
    </div>
  );
}
