"use client";

import useSWR from "swr";
import { fetchPmsHoldings, fetchPmsSectorHistory } from "@/lib/pms-api";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
} from "recharts";
import { formatPrice } from "@/lib/utils";

interface PmsAllocationProps {
  portfolioId: number;
}

const COLORS = [
  "#059669", "#2563eb", "#d97706", "#dc2626", "#7c3aed",
  "#0891b2", "#ea580c", "#4f46e5", "#16a34a", "#be123c",
  "#854d0e", "#0e7490", "#9333ea", "#c2410c",
];

export function PmsAllocation({ portfolioId }: PmsAllocationProps) {
  const { data: holdings, isLoading: holdingsLoading } = useSWR(
    `pms-holdings-${portfolioId}`,
    () => fetchPmsHoldings(portfolioId),
    { refreshInterval: 300_000 }
  );
  const { data: sectorHistory, isLoading: sectorLoading } = useSWR(
    `pms-sector-history-${portfolioId}`,
    () => fetchPmsSectorHistory(portfolioId),
    { refreshInterval: 300_000 }
  );

  if (holdingsLoading || sectorLoading) return <Skeleton className="h-64 rounded-xl" />;
  if (!holdings || holdings.by_stock.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5">
      <h3 className="text-sm font-semibold text-slate-700 mb-4">Portfolio Allocation</h3>

      <div className="flex gap-6 flex-col lg:flex-row">
        {/* Stock pie chart */}
        <StockPie data={holdings.by_stock} />

        {/* Sector history table */}
        {sectorHistory && sectorHistory.snapshots.length > 0 && (
          <SectorHistoryTable
            snapshots={sectorHistory.snapshots}
            sectors={sectorHistory.sectors}
          />
        )}
      </div>
    </div>
  );
}

// ─── Stock Pie (current holdings) ────────────────────────

function StockPie({ data }: { data: { label: string; value: number; pct: number }[] }) {
  return (
    <div className="flex-1 min-w-0">
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
        By Instrument (Current)
      </h4>
      <div className="flex items-center gap-4">
        <div className="w-36 h-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={65}
                paddingAngle={2}
              >
                {data.map((_, i) => (
                  <Cell key={i} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatPrice(value)}
                contentStyle={{ borderRadius: "8px", border: "1px solid #e2e8f0", fontSize: "12px" }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-1.5 flex-1 min-w-0">
          {data.map((item, i) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <div
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="truncate text-slate-700">{item.label}</span>
              <span className="ml-auto font-mono tabular-nums text-slate-500 shrink-0">
                {item.pct.toFixed(1)}%
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ─── Sector History Table ────────────────────────────────

function SectorHistoryTable({
  snapshots,
  sectors,
}: {
  snapshots: { label: string; date: string; sectors: Record<string, number> }[];
  sectors: string[];
}) {
  return (
    <div className="flex-1 min-w-0">
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
        Sector Allocation Over Time
      </h4>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="border-b border-slate-100">
              <th className="text-left py-2 pr-3 font-semibold text-slate-400 uppercase tracking-wider">
                Sector
              </th>
              {snapshots.map((s) => (
                <th
                  key={s.label}
                  className="text-right py-2 px-2 font-semibold text-slate-400 uppercase tracking-wider"
                >
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector) => (
              <tr key={sector} className="border-b border-slate-50 hover:bg-slate-50/50">
                <td className="py-1.5 pr-3 font-medium text-slate-700 whitespace-nowrap">
                  {sector}
                </td>
                {snapshots.map((snap) => {
                  const pct = snap.sectors[sector];
                  return (
                    <td
                      key={snap.label}
                      className="py-1.5 px-2 text-right font-mono tabular-nums text-slate-600"
                    >
                      {pct != null ? `${pct.toFixed(1)}%` : "—"}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
