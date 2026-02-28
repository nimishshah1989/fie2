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
import { Button } from "@/components/ui/button";
import { formatPrice, formatPct } from "@/lib/utils";
import type { PortfolioTransactionRow } from "@/lib/portfolio-types";
import { Download } from "lucide-react";
import { getTransactionsExportURL } from "@/lib/portfolio-api";

interface TransactionTableProps {
  transactions: PortfolioTransactionRow[];
  portfolioId: number;
}

export function TransactionTable({ transactions, portfolioId }: TransactionTableProps) {
  const [filter, setFilter] = useState<"ALL" | "BUY" | "SELL">("ALL");

  const filtered = filter === "ALL"
    ? transactions
    : transactions.filter((t) => t.txn_type === filter);

  return (
    <div className="space-y-3">
      {/* Filter + Export */}
      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {(["ALL", "BUY", "SELL"] as const).map((f) => (
            <Button
              key={f}
              variant={filter === f ? "default" : "outline"}
              size="sm"
              className="text-xs h-7 px-3"
              onClick={() => setFilter(f)}
            >
              {f} {f !== "ALL" && `(${transactions.filter((t) => t.txn_type === f).length})`}
            </Button>
          ))}
        </div>
        <a
          href={getTransactionsExportURL(portfolioId)}
          target="_blank"
          rel="noopener noreferrer"
        >
          <Button variant="outline" size="sm" className="text-xs h-7 gap-1">
            <Download className="h-3 w-3" />
            CSV
          </Button>
        </a>
      </div>

      {/* Table */}
      <div className="rounded-lg border border-border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/50">
              <TableHead className="w-[90px]">Date</TableHead>
              <TableHead className="w-[60px]">Type</TableHead>
              <TableHead>Ticker</TableHead>
              <TableHead className="text-right">Qty</TableHead>
              <TableHead className="text-right">Price</TableHead>
              <TableHead className="text-right">Total</TableHead>
              <TableHead className="text-right">P&L</TableHead>
              <TableHead>Notes</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} className="text-center text-muted-foreground py-8">
                  No transactions found
                </TableCell>
              </TableRow>
            )}
            {filtered.map((t) => (
              <TableRow key={t.id} className="hover:bg-muted/30">
                <TableCell className="text-xs font-mono">{t.txn_date}</TableCell>
                <TableCell>
                  <Badge
                    variant="outline"
                    className={`text-[10px] ${
                      t.txn_type === "BUY"
                        ? "border-emerald-300 text-emerald-700 bg-emerald-50"
                        : "border-red-300 text-red-700 bg-red-50"
                    }`}
                  >
                    {t.txn_type}
                  </Badge>
                </TableCell>
                <TableCell className="font-medium text-sm">{t.ticker}</TableCell>
                <TableCell className="text-right font-mono text-sm">{t.quantity}</TableCell>
                <TableCell className="text-right font-mono text-sm">{formatPrice(t.price)}</TableCell>
                <TableCell className="text-right font-mono text-sm">{formatPrice(t.total_value)}</TableCell>
                <TableCell className={`text-right font-mono text-sm font-semibold ${
                  t.realized_pnl != null
                    ? t.realized_pnl >= 0 ? "text-emerald-600" : "text-red-600"
                    : "text-muted-foreground"
                }`}>
                  {t.realized_pnl != null ? (
                    <div>
                      <div>{formatPrice(t.realized_pnl)}</div>
                      <div className="text-[10px]">{formatPct(t.realized_pnl_pct)}</div>
                    </div>
                  ) : "—"}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground max-w-[120px] truncate">
                  {t.notes || "—"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
