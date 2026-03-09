"use client";

import useSWR from "swr";
import { fetchPmsHoldings, fetchPmsSectorHistory } from "@/lib/pms-api";
import { Skeleton } from "@/components/ui/skeleton";
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from "recharts";
import { formatPrice } from "@/lib/utils";
import { getSectorHex } from "@/lib/constants";

interface PmsAllocationProps {
  portfolioId: number;
}

// Fallback colors for stock pie (sector pie uses getSectorHex)
const STOCK_COLORS = [
  "#059669", "#2563eb", "#d97706", "#dc2626", "#7c3aed",
  "#0891b2", "#ea580c", "#4f46e5", "#16a34a", "#be123c",
  "#854d0e", "#0e7490", "#9333ea", "#c2410c",
];

export function PmsAllocation({ portfolioId }: PmsAllocationProps) {
  const { data: holdings, isLoading: holdingsLoading } = useSWR(
    `pms-holdings-${portfolioId}`,
    () => fetchPmsHoldings(portfolioId),
    { refreshInterval: 900_000 }
  );
  const { data: sectorHistory, isLoading: sectorLoading } = useSWR(
    `pms-sector-history-${portfolioId}`,
    () => fetchPmsSectorHistory(portfolioId),
    { refreshInterval: 900_000 }
  );

  if (holdingsLoading || sectorLoading) return <Skeleton className="h-64 rounded-xl" />;
  if (!holdings || holdings.by_stock.length === 0) return null;

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 space-y-6">
      <h3 className="text-sm font-semibold text-slate-700">Portfolio Allocation</h3>

      {/* Section A: Two pie charts side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <AllocationPie
          title="By Instrument"
          data={holdings.by_stock}
          colorMode="indexed"
        />
        {holdings.by_sector.length > 0 && (
          <AllocationPie
            title="By Sector"
            data={holdings.by_sector}
            colorMode="sector"
          />
        )}
      </div>

      {/* Section B: Sector History Heatmap Table */}
      {sectorHistory && sectorHistory.snapshots.length > 0 && (
        <SectorHeatmapTable
          snapshots={sectorHistory.snapshots}
          sectors={sectorHistory.sectors}
        />
      )}

      {/* Section C: Stacked Bar Chart — sector allocation shifts */}
      {sectorHistory && sectorHistory.snapshots.length > 0 && (
        <AllocationShiftChart
          snapshots={sectorHistory.snapshots}
          sectors={sectorHistory.sectors}
        />
      )}
    </div>
  );
}

// ─── Pie Chart (used for both stock + sector) ────────────

function AllocationPie({
  title,
  data,
  colorMode,
}: {
  title: string;
  data: { label: string; value: number; pct: number }[];
  colorMode: "indexed" | "sector";
}) {
  const getColor = (item: { label: string }, index: number) =>
    colorMode === "sector"
      ? getSectorHex(item.label)
      : STOCK_COLORS[index % STOCK_COLORS.length];

  return (
    <div>
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
        {title}
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
                {data.map((item, i) => (
                  <Cell key={item.label} fill={getColor(item, i)} />
                ))}
              </Pie>
              <Tooltip
                formatter={(value: number) => formatPrice(value)}
                contentStyle={{
                  borderRadius: "8px",
                  border: "1px solid #e2e8f0",
                  fontSize: "12px",
                }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-1.5 flex-1 min-w-0">
          {data.map((item, i) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <div
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ backgroundColor: getColor(item, i) }}
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

// ─── Sector History Heatmap Table ────────────────────────

function SectorHeatmapTable({
  snapshots,
  sectors,
}: {
  snapshots: { label: string; date: string; sectors: Record<string, number> }[];
  sectors: string[];
}) {
  // Compute max percentage across all cells for intensity scaling
  const maxPct = Math.max(
    ...snapshots.flatMap((s) => Object.values(s.sectors)),
    1
  );

  return (
    <div>
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
                  className="text-center py-2 px-2 font-semibold text-slate-400 uppercase tracking-wider"
                >
                  {s.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {sectors.map((sector) => {
              const sectorHex = getSectorHex(sector);
              return (
                <tr key={sector} className="border-b border-slate-50">
                  <td className="py-1.5 pr-3 whitespace-nowrap">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: sectorHex }}
                      />
                      <span className="font-medium text-slate-700">{sector}</span>
                    </div>
                  </td>
                  {snapshots.map((snap) => {
                    const pct = snap.sectors[sector];
                    const intensity = pct != null ? pct / maxPct : 0;
                    const bgColor =
                      pct != null
                        ? hexToRgba(sectorHex, intensity * 0.3)
                        : "transparent";

                    return (
                      <td
                        key={snap.label}
                        className="py-1.5 px-2 text-center font-mono tabular-nums text-slate-700 rounded"
                        style={{ backgroundColor: bgColor }}
                      >
                        {pct != null ? `${pct.toFixed(1)}%` : "—"}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Stacked Bar Chart — allocation shift over time ──────

function AllocationShiftChart({
  snapshots,
  sectors,
}: {
  snapshots: { label: string; date: string; sectors: Record<string, number> }[];
  sectors: string[];
}) {
  // Reverse so bars go from oldest (12M) on left to Today on right
  // Normalize each snapshot to sum exactly 100% to avoid rounding errors (100.1%)
  const chartData = [...snapshots].reverse().map((snap) => {
    const entry: Record<string, string | number> = { period: snap.label };
    const rawTotal = sectors.reduce((sum, s) => sum + (snap.sectors[s] ?? 0), 0);
    const scale = rawTotal > 0 ? 100 / rawTotal : 1;
    for (const sector of sectors) {
      const raw = snap.sectors[sector] ?? 0;
      entry[sector] = Math.round(raw * scale * 10) / 10;
    }
    return entry;
  });

  // Only show sectors that have at least one non-zero value
  const activeSectors = sectors.filter((sector) =>
    snapshots.some((s) => (s.sectors[sector] ?? 0) > 0)
  );

  return (
    <div>
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wide mb-3">
        Allocation Shift
      </h4>
      <div className="h-48">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={chartData} barCategoryGap="20%">
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 11, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
            />
            <YAxis
              tick={{ fontSize: 11, fill: "#64748b" }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v: number) => `${v}%`}
              domain={[0, 100]}
            />
            <Tooltip
              formatter={(value: number, name: string) => [`${value.toFixed(1)}%`, name]}
              contentStyle={{
                borderRadius: "8px",
                border: "1px solid #e2e8f0",
                fontSize: "12px",
              }}
            />
            {activeSectors.map((sector) => (
              <Bar
                key={sector}
                dataKey={sector}
                stackId="allocation"
                fill={getSectorHex(sector)}
                radius={0}
              />
            ))}
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// ─── Helpers ─────────────────────────────────────────────

/** Convert hex color to rgba with given opacity */
function hexToRgba(hex: string, alpha: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
