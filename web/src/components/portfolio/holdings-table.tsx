"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";
import { formatPrice, formatPct } from "@/lib/utils";
import type { PortfolioHoldingRow, HoldingsTotals } from "@/lib/portfolio-types";
import { ArrowUpDown, TrendingUp, TrendingDown } from "lucide-react";

// Sector color mapping — consistent colors for each sector
const SECTOR_COLORS: Record<string, { bg: string; text: string; bar: string }> = {
  "Banking":            { bg: "bg-blue-50",    text: "text-blue-700",     bar: "bg-blue-400" },
  "IT":                 { bg: "bg-violet-50",  text: "text-violet-700",   bar: "bg-violet-400" },
  "Pharma":             { bg: "bg-pink-50",    text: "text-pink-700",     bar: "bg-pink-400" },
  "Energy":             { bg: "bg-amber-50",   text: "text-amber-700",    bar: "bg-amber-400" },
  "Auto":               { bg: "bg-cyan-50",    text: "text-cyan-700",     bar: "bg-cyan-400" },
  "FMCG":               { bg: "bg-green-50",   text: "text-green-700",    bar: "bg-green-400" },
  "Metal":              { bg: "bg-slate-100",  text: "text-slate-700",    bar: "bg-slate-400" },
  "Realty":             { bg: "bg-orange-50",  text: "text-orange-700",   bar: "bg-orange-400" },
  "Infra":              { bg: "bg-stone-50",   text: "text-stone-700",    bar: "bg-stone-400" },
  "Telecom":            { bg: "bg-indigo-50",  text: "text-indigo-700",   bar: "bg-indigo-400" },
  "Media":              { bg: "bg-fuchsia-50", text: "text-fuchsia-700",  bar: "bg-fuchsia-400" },
  "Financial Services": { bg: "bg-teal-50",    text: "text-teal-700",     bar: "bg-teal-400" },
  "Cash":               { bg: "bg-emerald-50", text: "text-emerald-700",  bar: "bg-emerald-400" },
  "ETF":                { bg: "bg-sky-50",     text: "text-sky-700",      bar: "bg-sky-400" },
  "Other":              { bg: "bg-gray-50",    text: "text-gray-600",     bar: "bg-gray-400" },
};

function getSectorColor(sector: string | null) {
  if (!sector) return SECTOR_COLORS["Other"];
  return SECTOR_COLORS[sector] || SECTOR_COLORS["Other"];
}

interface HoldingsTableProps {
  holdings: PortfolioHoldingRow[];
  totals: HoldingsTotals | null;
  onBuyMore?: (ticker: string, sector: string | null) => void;
  onSell?: (ticker: string) => void;
}

type SortKey = "ticker" | "quantity" | "avg_cost" | "current_price" | "current_value" | "unrealized_pnl_pct" | "weight_pct";

export function HoldingsTable({ holdings, totals, onBuyMore, onSell }: HoldingsTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("weight_pct");
  const [sortDesc, setSortDesc] = useState(true);

  function handleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDesc(!sortDesc);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  }

  const sorted = [...holdings].sort((a, b) => {
    const av = a[sortKey] ?? 0;
    const bv = b[sortKey] ?? 0;
    if (typeof av === "string" && typeof bv === "string") {
      return sortDesc ? bv.localeCompare(av) : av.localeCompare(bv);
    }
    return sortDesc ? (bv as number) - (av as number) : (av as number) - (bv as number);
  });

  // Find max weight for allocation bar scaling
  const maxWeight = Math.max(...holdings.map((h) => h.weight_pct ?? 0), 1);

  function SortHeader({ label, field, align }: { label: string; field: SortKey; align?: string }) {
    const isActive = sortKey === field;
    return (
      <button
        className={`flex items-center gap-1 hover:text-foreground transition-colors ${align === "center" ? "mx-auto" : align === "right" ? "ml-auto" : ""}`}
        onClick={() => handleSort(field)}
      >
        {label}
        <ArrowUpDown className={`h-3 w-3 ${isActive ? "text-primary" : "text-muted-foreground/50"}`} />
      </button>
    );
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/50">
            <TableHead className="w-[180px]"><SortHeader label="Ticker" field="ticker" /></TableHead>
            <TableHead className="text-center w-[60px]"><SortHeader label="Qty" field="quantity" align="center" /></TableHead>
            <TableHead className="text-center w-[100px]"><SortHeader label="Avg Cost" field="avg_cost" align="center" /></TableHead>
            <TableHead className="text-center w-[100px]"><SortHeader label="CMP" field="current_price" align="center" /></TableHead>
            <TableHead className="text-center w-[110px]"><SortHeader label="Value" field="current_value" align="center" /></TableHead>
            <TableHead className="text-center w-[90px]"><SortHeader label="P&L %" field="unrealized_pnl_pct" align="center" /></TableHead>
            <TableHead className="w-[150px]"><SortHeader label="Weight" field="weight_pct" /></TableHead>
            {(onBuyMore || onSell) && <TableHead className="w-[100px] text-center">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((h) => {
            const pnlColor = (h.unrealized_pnl_pct ?? 0) >= 0 ? "text-emerald-600" : "text-red-600";
            const sectorColor = getSectorColor(h.sector);
            const weightPct = h.weight_pct ?? 0;
            const barWidth = maxWeight > 0 ? (weightPct / maxWeight) * 100 : 0;

            return (
              <TableRow key={h.id} className="hover:bg-muted/30 group">
                {/* Ticker + Sector Badge */}
                <TableCell className="font-medium">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold">{h.ticker}</span>
                    {h.sector && (
                      <span className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ${sectorColor.bg} ${sectorColor.text}`}>
                        {h.sector}
                      </span>
                    )}
                  </div>
                </TableCell>

                {/* Quantity */}
                <TableCell className="text-center font-mono text-sm tabular-nums">{h.quantity}</TableCell>

                {/* Avg Cost */}
                <TableCell className="text-center font-mono text-sm tabular-nums">{formatPrice(h.avg_cost)}</TableCell>

                {/* CMP */}
                <TableCell className="text-center font-mono text-sm tabular-nums">
                  {h.current_price ? formatPrice(h.current_price) : (
                    <span className="text-muted-foreground">{"—"}</span>
                  )}
                </TableCell>

                {/* Current Value */}
                <TableCell className="text-center font-mono text-sm tabular-nums">
                  {formatPrice(h.current_value ?? h.total_cost)}
                </TableCell>

                {/* P&L % */}
                <TableCell className={`text-center font-mono text-sm font-semibold tabular-nums ${pnlColor}`}>
                  {h.unrealized_pnl_pct != null ? formatPct(h.unrealized_pnl_pct) : "—"}
                </TableCell>

                {/* Weight with allocation bar */}
                <TableCell>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-sm tabular-nums w-[45px] text-right">
                      {weightPct.toFixed(1)}%
                    </span>
                    <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${sectorColor.bar}`}
                        style={{ width: `${barWidth}%`, opacity: 0.7 }}
                      />
                    </div>
                  </div>
                </TableCell>

                {/* Action Buttons */}
                {(onBuyMore || onSell) && (
                  <TableCell className="text-center">
                    <div className="flex items-center justify-center gap-1">
                      {onBuyMore && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-emerald-600 hover:text-emerald-700 hover:bg-emerald-50"
                          onClick={() => onBuyMore(h.ticker, h.sector)}
                          title="Buy more"
                        >
                          <TrendingUp className="h-3.5 w-3.5" />
                        </Button>
                      )}
                      {onSell && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-6 w-6 p-0 text-red-600 hover:text-red-700 hover:bg-red-50"
                          onClick={() => onSell(h.ticker)}
                          title="Sell"
                        >
                          <TrendingDown className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </div>
                  </TableCell>
                )}
              </TableRow>
            );
          })}

          {/* Totals Row */}
          {totals && (
            <TableRow className="bg-muted/50 font-semibold border-t-2">
              <TableCell className="text-sm">TOTAL ({totals.num_holdings})</TableCell>
              <TableCell />
              <TableCell className="text-center font-mono text-sm tabular-nums">
                {formatPrice(totals.total_invested)}
              </TableCell>
              <TableCell />
              <TableCell className="text-center font-mono text-sm tabular-nums">
                {formatPrice(totals.current_value)}
              </TableCell>
              <TableCell className={`text-center font-mono text-sm tabular-nums ${
                totals.unrealized_pnl_pct >= 0 ? "text-emerald-600" : "text-red-600"
              }`}>
                {formatPct(totals.unrealized_pnl_pct)}
              </TableCell>
              <TableCell className="font-mono text-sm">
                <div className="flex items-center gap-2">
                  <span className="w-[45px] text-right">100%</span>
                  <div className="flex-1 h-3 bg-slate-100 rounded-full overflow-hidden">
                    <div className="h-full rounded-full bg-slate-400 opacity-70" style={{ width: "100%" }} />
                  </div>
                </div>
              </TableCell>
              {(onBuyMore || onSell) && <TableCell />}
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
