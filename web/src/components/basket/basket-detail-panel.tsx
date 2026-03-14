"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { X, Pencil, Archive, StopCircle, Calendar } from "lucide-react";
import { cn, formatPrice } from "@/lib/utils";
import { archiveBasket, stopBasket } from "@/lib/basket-api";
import type { BasketLiveItem } from "@/lib/basket-types";
import type { UpdateBasketPayload } from "@/lib/basket-types";

interface BasketDetailPanelProps {
  basket: BasketLiveItem;
  onClose: () => void;
  onEdit: (basket: BasketLiveItem) => void;
  onMutate: () => void;
}

const PERIOD_LABELS = [
  { key: "1d", label: "1D" },
  { key: "1w", label: "1W" },
  { key: "1m", label: "1M" },
  { key: "3m", label: "3M" },
  { key: "6m", label: "6M" },
  { key: "12m", label: "12M" },
];

function ReturnCell({ value }: { value: number | null | undefined }) {
  if (value == null) return <span className="text-muted-foreground">---</span>;
  const color = value >= 0 ? "text-emerald-600" : "text-red-600";
  return (
    <span className={cn("font-mono text-xs", color)}>
      {value >= 0 ? "+" : ""}{value.toFixed(2)}%
    </span>
  );
}

function formatINR(val: number): string {
  return `₹${val.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function BasketDetailPanel({ basket, onClose, onEdit, onMutate }: BasketDetailPanelProps) {
  const [archiving, setArchiving] = useState(false);
  const [stopping, setStopping] = useState(false);
  const hasPortfolioSize = basket.portfolio_size != null && basket.portfolio_size > 0;
  const isStopped = !!basket.exit_date;

  const portfolioSize = basket.portfolio_size ?? 0;
  const deployed = basket.portfolio_cost ?? 0;
  const stockWorth = basket.constituents.reduce((s, c) => s + (c.current_worth ?? 0), 0);
  const unallocatedCash = portfolioSize > 0 && deployed > 0 ? portfolioSize - deployed : 0;
  const stockPnl = deployed > 0 && stockWorth > 0 ? stockWorth - deployed : null;
  const stockPnlPct = (stockPnl != null && deployed > 0) ? (stockPnl / deployed) * 100 : null;

  // Table totals
  const totalUnits = basket.constituents.reduce((s, c) => s + (c.computed_units ?? 0), 0);
  const totalCost = basket.constituents.reduce((s, c) => s + (c.cost_value ?? 0), 0);

  async function handleArchive() {
    if (!confirm(`Archive basket "${basket.name}"? It will be hidden from the dashboard.`)) return;
    setArchiving(true);
    try {
      await archiveBasket(basket.id);
      onMutate();
      onClose();
    } finally {
      setArchiving(false);
    }
  }

  async function handleStop() {
    if (!confirm(`Stop basket "${basket.name}"? Returns will be frozen at today's date.`)) return;
    setStopping(true);
    try {
      await stopBasket(basket.id);
      onMutate();
      onClose();
    } finally {
      setStopping(false);
    }
  }

  return (
    <Card className="gap-0">
      <CardContent className="p-4 sm:p-6 space-y-4">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h3 className="text-lg font-bold text-foreground">{basket.name}</h3>
            {basket.description && (
              <p className="text-xs text-muted-foreground mt-0.5">{basket.description}</p>
            )}
            <div className="flex items-center gap-2 mt-1 flex-wrap">
              <Badge variant="outline" className="text-[10px]">
                {basket.slug}
              </Badge>
              <span className="text-xs text-muted-foreground">
                vs {basket.benchmark}
              </span>
              {hasPortfolioSize && (
                <Badge variant="secondary" className="text-[10px] font-mono">
                  {formatINR(portfolioSize)}
                </Badge>
              )}
              {basket.execution_date && (
                <span className="flex items-center gap-1 text-[10px] text-slate-500">
                  <Calendar className="h-3 w-3" />
                  Started {basket.execution_date}
                </span>
              )}
              {isStopped && (
                <Badge className="text-[10px] bg-amber-100 text-amber-700 border-amber-300">
                  Stopped {basket.exit_date}
                </Badge>
              )}
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => onEdit(basket)} title="Edit basket">
              <Pencil className="h-4 w-4" />
            </Button>
            {!isStopped && (
              <Button
                variant="ghost"
                size="sm"
                onClick={handleStop}
                disabled={stopping}
                title="Stop basket — freeze returns at today"
                className="text-amber-600 hover:text-amber-800"
              >
                <StopCircle className="h-4 w-4" />
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={handleArchive}
              disabled={archiving}
              title="Archive basket"
              className="text-red-500 hover:text-red-700"
            >
              <Archive className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="sm" onClick={onClose}>
              <X className="h-4 w-4" />
            </Button>
          </div>
        </div>

        {/* NAV Index Value */}
        {basket.current_value != null && (
          <div className="flex items-baseline gap-3">
            <span className="text-2xl font-bold font-mono">
              {basket.current_value.toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2,
              })}
            </span>
            {basket.change_pct != null && (
              <span className={cn(
                "text-sm font-mono",
                basket.change_pct >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {basket.change_pct >= 0 ? "+" : ""}{basket.change_pct.toFixed(2)}%
              </span>
            )}
          </div>
        )}

        {/* Portfolio Worth Cards */}
        {hasPortfolioSize && deployed > 0 && (
          <div>
            <div className="grid grid-cols-3 gap-3">
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Deployed</p>
                <p className="text-sm font-bold font-mono mt-0.5">
                  {formatINR(deployed)}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Current Value</p>
                <p className="text-sm font-bold font-mono mt-0.5">
                  {stockWorth > 0 ? formatINR(stockWorth) : "—"}
                </p>
              </div>
              <div className="bg-slate-50 rounded-lg p-3">
                <p className="text-[10px] text-slate-500 uppercase tracking-wider">Returns</p>
                {stockPnl != null && stockPnlPct != null ? (
                  <p className={cn(
                    "text-sm font-bold font-mono mt-0.5",
                    stockPnl >= 0 ? "text-emerald-600" : "text-red-600"
                  )}>
                    {stockPnl >= 0 ? "+" : ""}₹{Math.abs(stockPnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                    <span className="text-[10px] ml-1">
                      ({stockPnlPct >= 0 ? "+" : ""}{stockPnlPct.toFixed(2)}%)
                    </span>
                  </p>
                ) : (
                  <p className="text-sm font-mono text-muted-foreground mt-0.5">—</p>
                )}
              </div>
            </div>
            {unallocatedCash > 0 && (
              <p className="text-[10px] text-slate-400 mt-1.5">
                {formatINR(unallocatedCash)} unallocated cash (whole-unit rounding)
              </p>
            )}
          </div>
        )}

        {/* Period Returns Strip */}
        <div className="space-y-2">
          <div className="grid grid-cols-7 gap-1 text-center text-[10px]">
            <div className="font-semibold text-muted-foreground">Returns</div>
            {PERIOD_LABELS.map((p) => (
              <div key={p.key} className="font-semibold text-muted-foreground">{p.label}</div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            <div className="text-[10px] text-muted-foreground text-left">Index</div>
            {PERIOD_LABELS.map((p) => (
              <div key={p.key}>
                <ReturnCell value={basket.index_returns?.[p.key]} />
              </div>
            ))}
          </div>
          <div className="grid grid-cols-7 gap-1 text-center">
            <div className="text-[10px] text-muted-foreground text-left">Ratio</div>
            {PERIOD_LABELS.map((p) => (
              <div key={p.key}>
                <ReturnCell value={basket.ratio_returns?.[p.key]} />
              </div>
            ))}
          </div>
        </div>

        {/* Constituents Table */}
        <div>
          <h4 className="text-sm font-semibold mb-2">
            Constituents ({basket.num_constituents})
          </h4>
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="text-xs">Ticker</TableHead>
                  <TableHead className="text-xs">Company</TableHead>
                  <TableHead className="text-xs text-right">Weight</TableHead>
                  {hasPortfolioSize && (
                    <>
                      <TableHead className="text-xs text-right">Price</TableHead>
                      <TableHead className="text-xs text-right">Units</TableHead>
                      <TableHead className="text-xs text-right">Worth</TableHead>
                      <TableHead className="text-xs text-right">P&L</TableHead>
                    </>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {basket.constituents.map((c) => {
                  const pnl = (c.current_worth != null && c.cost_value != null)
                    ? c.current_worth - c.cost_value
                    : null;
                  return (
                    <TableRow key={c.ticker}>
                      <TableCell className="font-mono text-xs font-medium">
                        {c.ticker}
                      </TableCell>
                      <TableCell className="text-xs text-muted-foreground truncate max-w-[150px]">
                        {c.company_name || "—"}
                      </TableCell>
                      <TableCell className="text-xs text-right font-mono">
                        {c.weight_pct.toFixed(1)}%
                      </TableCell>
                      {hasPortfolioSize && (
                        <>
                          <TableCell className="text-xs text-right font-mono">
                            {c.current_price != null
                              ? formatPrice(c.current_price)
                              : "—"}
                          </TableCell>
                          <TableCell className="text-xs text-right font-mono font-semibold">
                            {c.computed_units != null ? c.computed_units.toFixed(0) : "—"}
                          </TableCell>
                          <TableCell className="text-xs text-right font-mono">
                            {c.current_worth != null ? formatINR(c.current_worth) : "—"}
                          </TableCell>
                          <TableCell className={cn(
                            "text-xs text-right font-mono",
                            pnl != null && pnl >= 0 ? "text-emerald-600" : "text-red-600"
                          )}>
                            {pnl != null
                              ? `${pnl >= 0 ? "+" : ""}₹${Math.abs(pnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                              : "—"}
                          </TableCell>
                        </>
                      )}
                    </TableRow>
                  );
                })}
                {/* Totals row */}
                {hasPortfolioSize && (
                  <TableRow className="bg-muted/30 border-t-2">
                    <TableCell className="text-xs font-bold" colSpan={3}>
                      Total
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">—</TableCell>
                    <TableCell className="text-xs text-right font-mono font-bold">
                      {totalUnits}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono font-bold">
                      {stockWorth > 0 ? formatINR(stockWorth) : "—"}
                    </TableCell>
                    <TableCell className={cn(
                      "text-xs text-right font-mono font-bold",
                      stockPnl != null && stockPnl >= 0 ? "text-emerald-600" : "text-red-600"
                    )}>
                      {stockPnl != null
                        ? `${stockPnl >= 0 ? "+" : ""}₹${Math.abs(stockPnl).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                        : "—"}
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
