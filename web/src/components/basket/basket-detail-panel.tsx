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
import { X, Pencil, Archive } from "lucide-react";
import { cn, formatPrice } from "@/lib/utils";
import { archiveBasket } from "@/lib/basket-api";
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

export function BasketDetailPanel({ basket, onClose, onEdit, onMutate }: BasketDetailPanelProps) {
  const [archiving, setArchiving] = useState(false);

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
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline" className="text-[10px]">
                {basket.slug}
              </Badge>
              <span className="text-xs text-muted-foreground">
                vs {basket.benchmark}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="sm" onClick={() => onEdit(basket)} title="Edit basket">
              <Pencil className="h-4 w-4" />
            </Button>
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

        {/* Current value */}
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

        {/* Period Returns Strip */}
        <div className="space-y-2">
          <div className="grid grid-cols-7 gap-1 text-center text-[10px]">
            <div className="font-semibold text-muted-foreground">Returns</div>
            {PERIOD_LABELS.map((p) => (
              <div key={p.key} className="font-semibold text-muted-foreground">{p.label}</div>
            ))}
          </div>
          {/* Index returns */}
          <div className="grid grid-cols-7 gap-1 text-center">
            <div className="text-[10px] text-muted-foreground text-left">Index</div>
            {PERIOD_LABELS.map((p) => (
              <div key={p.key}>
                <ReturnCell value={basket.index_returns?.[p.key]} />
              </div>
            ))}
          </div>
          {/* Ratio returns */}
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
                </TableRow>
              </TableHeader>
              <TableBody>
                {basket.constituents.map((c) => (
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
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
