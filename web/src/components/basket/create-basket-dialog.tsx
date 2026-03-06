"use client";

import { useState, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Plus, Trash2 } from "lucide-react";
import { createBasket, updateBasket } from "@/lib/basket-api";
import { BASE_INDEX_OPTIONS } from "@/lib/constants";
import type { BasketLiveItem, ConstituentInput } from "@/lib/basket-types";

export interface BasketPrefill {
  name: string;
  benchmark: string;
  constituents: ConstituentInput[];
}

interface CreateBasketDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
  editBasket?: BasketLiveItem | null;
  prefill?: BasketPrefill | null;
}

function emptyRow(): ConstituentInput {
  return { ticker: "", company_name: "", weight_pct: 0, buy_price: 0 };
}

export function CreateBasketDialog({ open, onOpenChange, onSuccess, editBasket, prefill }: CreateBasketDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [benchmark, setBenchmark] = useState("NIFTY");
  const [portfolioSize, setPortfolioSize] = useState("");
  const [rows, setRows] = useState<ConstituentInput[]>([emptyRow()]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const isEdit = !!editBasket;

  // Pre-fill when editing or from prefill (recommendation → microbasket)
  useEffect(() => {
    if (editBasket) {
      setName(editBasket.name);
      setDescription(editBasket.description || "");
      setBenchmark(editBasket.benchmark);
      setPortfolioSize(editBasket.portfolio_size ? String(editBasket.portfolio_size) : "");
      setRows(
        editBasket.constituents.map((c) => ({
          ticker: c.ticker,
          company_name: c.company_name || "",
          weight_pct: c.weight_pct,
          buy_price: c.buy_price ?? c.current_price ?? 0,
        }))
      );
    } else if (prefill) {
      setName(prefill.name);
      setDescription("");
      setBenchmark(prefill.benchmark);
      setPortfolioSize("");
      setRows(prefill.constituents.map((c) => ({
        ticker: c.ticker,
        company_name: c.company_name || "",
        weight_pct: c.weight_pct,
        buy_price: c.buy_price ?? 0,
      })));
    } else {
      setName("");
      setDescription("");
      setBenchmark("NIFTY");
      setPortfolioSize("");
      setRows([emptyRow()]);
    }
    setError("");
  }, [editBasket, prefill, open]);

  const totalWeight = rows.reduce((sum, r) => sum + (r.weight_pct || 0), 0);
  const weightValid = Math.abs(totalWeight - 100) <= 1;

  function addRow() {
    setRows([...rows, emptyRow()]);
  }

  function removeRow(index: number) {
    if (rows.length <= 1) return;
    setRows(rows.filter((_, i) => i !== index));
  }

  function updateRow(index: number, field: keyof ConstituentInput, value: string | number) {
    setRows(rows.map((r, i) => (i === index ? { ...r, [field]: value } : r)));
  }

  async function handleSubmit() {
    setError("");

    // Validate
    const validRows = rows.filter((r) => r.ticker.trim() && r.weight_pct > 0);
    if (!name.trim()) {
      setError("Basket name is required");
      return;
    }
    if (validRows.length === 0) {
      setError("Add at least one constituent with a ticker and weight");
      return;
    }
    const sum = validRows.reduce((s, r) => s + r.weight_pct, 0);
    if (Math.abs(sum - 100) > 1) {
      setError(`Weights sum to ${sum.toFixed(1)}%, must be ~100%`);
      return;
    }

    setSubmitting(true);
    try {
      const constituents = validRows.map((r) => ({
        ticker: r.ticker.trim().toUpperCase(),
        company_name: r.company_name?.trim() || undefined,
        weight_pct: r.weight_pct,
        buy_price: (r.buy_price ?? 0) > 0 ? r.buy_price : undefined,
      }));

      const parsedSize = parseFloat(portfolioSize);
      // Auto-compute from buy_price × weight if portfolio_size not explicitly set
      let sizeValue = parsedSize > 0 ? parsedSize : undefined;
      if (!sizeValue) {
        const allHavePrices = validRows.every((r) => (r.buy_price ?? 0) > 0);
        if (allHavePrices && sizeValue === undefined) {
          // Sum of price × computed units (price × weight% / 100 × assumed base)
          // Cannot compute without qty — leave for backend auto-compute
          sizeValue = undefined;
        }
      }

      let result;
      if (isEdit && editBasket) {
        result = await updateBasket(editBasket.id, {
          name: name.trim(),
          description: description.trim() || undefined,
          benchmark,
          portfolio_size: sizeValue,
          constituents,
        });
      } else {
        result = await createBasket({
          name: name.trim(),
          description: description.trim() || undefined,
          benchmark,
          portfolio_size: sizeValue,
          constituents,
        });
      }

      if (result.success) {
        onOpenChange(false);
        onSuccess();
      } else {
        setError(result.error || "Failed to save basket");
      }
    } catch {
      setError("Network error — please try again");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? "Edit Basket" : "Create Microbasket"}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Name & Benchmark */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div>
              <Label htmlFor="basket-name">Basket Name</Label>
              <Input
                id="basket-name"
                placeholder="e.g. Healthcare India"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="mt-1"
              />
            </div>
            <div>
              <Label htmlFor="basket-bench">Benchmark</Label>
              <Select value={benchmark} onValueChange={setBenchmark}>
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {BASE_INDEX_OPTIONS.map((opt) => (
                    <SelectItem key={opt} value={opt}>{opt}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Description */}
          <div>
            <Label htmlFor="basket-desc">Description (optional)</Label>
            <Textarea
              id="basket-desc"
              placeholder="Brief description of this basket's theme..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              className="mt-1"
              rows={2}
            />
          </div>

          {/* Portfolio Size */}
          <div>
            <Label htmlFor="basket-size">Portfolio Size in ₹ (optional)</Label>
            <Input
              id="basket-size"
              type="number"
              placeholder="e.g. 500000"
              value={portfolioSize}
              onChange={(e) => setPortfolioSize(e.target.value)}
              className="mt-1 font-mono"
              min={0}
              step={1000}
            />
            <p className="text-[10px] text-muted-foreground mt-1">
              Auto-computed from buy price × units if not set manually
            </p>
          </div>

          {/* Constituents */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <Label>Constituents</Label>
              <span className={`text-xs font-mono ${weightValid ? "text-emerald-600" : "text-red-600"}`}>
                Total: {totalWeight.toFixed(1)}%
              </span>
            </div>

            <div className="space-y-2">
              {/* Header */}
              <div className="grid grid-cols-[1fr_1.2fr_70px_80px_70px_32px] gap-2 text-[10px] font-semibold text-muted-foreground uppercase">
                <span>Ticker</span>
                <span>Company Name</span>
                <span className="text-right">Wt %</span>
                <span className="text-right">Price ₹</span>
                <span className="text-right">Units</span>
                <span />
              </div>

              {rows.map((row, idx) => {
                const parsedSize = parseFloat(portfolioSize);
                const hasSize = parsedSize > 0;
                const hasPrice = (row.buy_price ?? 0) > 0;
                const units = hasSize && hasPrice && row.weight_pct > 0
                  ? Math.floor((row.weight_pct / 100) * parsedSize / row.buy_price!)
                  : null;
                return (
                  <div key={idx} className="grid grid-cols-[1fr_1.2fr_70px_80px_70px_32px] gap-2">
                    <Input
                      placeholder="RELIANCE"
                      value={row.ticker}
                      onChange={(e) => updateRow(idx, "ticker", e.target.value)}
                      className="font-mono text-sm"
                    />
                    <Input
                      placeholder="Reliance Industries"
                      value={row.company_name || ""}
                      onChange={(e) => updateRow(idx, "company_name", e.target.value)}
                      className="text-sm"
                    />
                    <Input
                      type="number"
                      placeholder="20"
                      value={row.weight_pct || ""}
                      onChange={(e) => updateRow(idx, "weight_pct", parseFloat(e.target.value) || 0)}
                      className="text-right font-mono text-sm"
                      min={0}
                      max={100}
                      step={0.1}
                    />
                    <Input
                      type="number"
                      placeholder="0"
                      value={row.buy_price || ""}
                      onChange={(e) => updateRow(idx, "buy_price", parseFloat(e.target.value) || 0)}
                      className="text-right font-mono text-sm"
                      min={0}
                      step={0.01}
                    />
                    <div className="flex items-center justify-end font-mono text-sm text-muted-foreground h-9 px-2">
                      {units != null ? units.toLocaleString("en-IN") : "—"}
                    </div>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeRow(idx)}
                      disabled={rows.length <= 1}
                      className="h-9 w-8 p-0 text-muted-foreground hover:text-red-500"
                    >
                      <Trash2 className="h-3.5 w-3.5" />
                    </Button>
                  </div>
                );
              })}
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={addRow}
              className="mt-2"
            >
              <Plus className="h-3.5 w-3.5 mr-1" />
              Add Stock
            </Button>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={submitting}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={submitting}>
              {submitting ? (isEdit ? "Saving..." : "Creating...") : (isEdit ? "Save Changes" : "Create Basket")}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
