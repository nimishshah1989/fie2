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
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatPct } from "@/lib/utils";
import type { PortfolioHoldingRow, HoldingsTotals } from "@/lib/portfolio-types";
import { ArrowUpDown } from "lucide-react";

interface HoldingsTableProps {
  holdings: PortfolioHoldingRow[];
  totals: HoldingsTotals | null;
}

type SortKey = "ticker" | "quantity" | "avg_cost" | "current_price" | "current_value" | "unrealized_pnl_pct" | "weight_pct";

export function HoldingsTable({ holdings, totals }: HoldingsTableProps) {
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

  function SortHeader({ label, field }: { label: string; field: SortKey }) {
    const isActive = sortKey === field;
    return (
      <button
        className="flex items-center gap-1 hover:text-foreground transition-colors"
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
            <TableHead className="w-[120px]"><SortHeader label="Ticker" field="ticker" /></TableHead>
            <TableHead className="text-right"><SortHeader label="Qty" field="quantity" /></TableHead>
            <TableHead className="text-right"><SortHeader label="Avg Cost" field="avg_cost" /></TableHead>
            <TableHead className="text-right"><SortHeader label="CMP" field="current_price" /></TableHead>
            <TableHead className="text-right"><SortHeader label="Value" field="current_value" /></TableHead>
            <TableHead className="text-right"><SortHeader label="P&L %" field="unrealized_pnl_pct" /></TableHead>
            <TableHead className="text-right"><SortHeader label="Weight" field="weight_pct" /></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((h) => {
            const pnlColor = (h.unrealized_pnl_pct ?? 0) >= 0 ? "text-emerald-600" : "text-red-600";
            return (
              <TableRow key={h.id} className="hover:bg-muted/30">
                <TableCell className="font-medium">
                  <div>
                    <span className="text-sm">{h.ticker}</span>
                    {h.sector && (
                      <Badge variant="outline" className="ml-2 text-[10px] py-0">
                        {h.sector}
                      </Badge>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-right font-mono text-sm">{h.quantity}</TableCell>
                <TableCell className="text-right font-mono text-sm">{formatPrice(h.avg_cost)}</TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {h.current_price ? formatPrice(h.current_price) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {formatPrice(h.current_value ?? h.total_cost)}
                </TableCell>
                <TableCell className={`text-right font-mono text-sm font-semibold ${pnlColor}`}>
                  {h.unrealized_pnl_pct != null ? formatPct(h.unrealized_pnl_pct) : "—"}
                </TableCell>
                <TableCell className="text-right font-mono text-sm">
                  {h.weight_pct != null ? `${h.weight_pct.toFixed(2)}%` : "—"}
                </TableCell>
              </TableRow>
            );
          })}

          {/* Totals Row */}
          {totals && (
            <TableRow className="bg-muted/50 font-semibold border-t-2">
              <TableCell className="text-sm">TOTAL ({totals.num_holdings})</TableCell>
              <TableCell />
              <TableCell />
              <TableCell />
              <TableCell className="text-right font-mono text-sm">
                {formatPrice(totals.current_value)}
              </TableCell>
              <TableCell className={`text-right font-mono text-sm ${
                totals.unrealized_pnl_pct >= 0 ? "text-emerald-600" : "text-red-600"
              }`}>
                {formatPct(totals.unrealized_pnl_pct)}
              </TableCell>
              <TableCell className="text-right font-mono text-sm">100%</TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
