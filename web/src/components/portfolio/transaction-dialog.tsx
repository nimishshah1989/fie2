"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createTransaction } from "@/lib/portfolio-api";
import { Plus } from "lucide-react";

const SECTOR_OPTIONS = [
  "Banking", "IT", "Pharma", "Energy", "Auto", "FMCG", "Metal",
  "Realty", "Infra", "Telecom", "Media", "Financial Services", "Other",
];

interface TransactionDialogProps {
  portfolioId: number;
  onCompleted: () => void;
  trigger?: React.ReactNode;
}

export function TransactionDialog({ portfolioId, onCompleted, trigger }: TransactionDialogProps) {
  const [open, setOpen] = useState(false);
  const [txnType, setTxnType] = useState<"BUY" | "SELL">("BUY");
  const [ticker, setTicker] = useState("");
  const [quantity, setQuantity] = useState("");
  const [price, setPrice] = useState("");
  const [txnDate, setTxnDate] = useState(new Date().toISOString().split("T")[0]);
  const [sector, setSector] = useState("");
  const [notes, setNotes] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    setTicker("");
    setQuantity("");
    setPrice("");
    setTxnDate(new Date().toISOString().split("T")[0]);
    setSector("");
    setNotes("");
    setError("");
  }

  async function handleSubmit() {
    setError("");
    const qty = parseInt(quantity);
    const px = parseFloat(price);
    if (!ticker.trim()) { setError("Ticker is required"); return; }
    if (isNaN(qty) || qty <= 0) { setError("Quantity must be positive"); return; }
    if (isNaN(px) || px <= 0) { setError("Price must be positive"); return; }
    if (!txnDate) { setError("Date is required"); return; }

    setLoading(true);
    try {
      const result = await createTransaction(portfolioId, {
        ticker: ticker.trim().toUpperCase(),
        txn_type: txnType,
        quantity: qty,
        price: px,
        txn_date: txnDate,
        notes: notes.trim() || undefined,
        sector: sector || undefined,
      });
      if (result.success) {
        setOpen(false);
        reset();
        onCompleted();
      } else {
        setError(result.error || "Transaction failed");
      }
    } catch {
      setError("Network error");
    } finally {
      setLoading(false);
    }
  }

  const totalValue = (parseInt(quantity) || 0) * (parseFloat(price) || 0);

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        {trigger || (
          <Button size="sm" className="gap-1.5">
            <Plus className="h-4 w-4" />
            Add Transaction
          </Button>
        )}
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Record Transaction</DialogTitle>
        </DialogHeader>
        <div className="space-y-4 pt-2">
          {/* BUY / SELL Toggle */}
          <div className="flex gap-2">
            <Button
              variant={txnType === "BUY" ? "default" : "outline"}
              size="sm"
              className={`flex-1 ${txnType === "BUY" ? "bg-emerald-600 hover:bg-emerald-700" : ""}`}
              onClick={() => setTxnType("BUY")}
            >
              BUY
            </Button>
            <Button
              variant={txnType === "SELL" ? "default" : "outline"}
              size="sm"
              className={`flex-1 ${txnType === "SELL" ? "bg-red-600 hover:bg-red-700" : ""}`}
              onClick={() => setTxnType("SELL")}
            >
              SELL
            </Button>
          </div>

          {/* Ticker */}
          <div className="space-y-1.5">
            <Label htmlFor="ticker">NSE Ticker</Label>
            <Input
              id="ticker"
              placeholder="e.g. RELIANCE"
              value={ticker}
              onChange={(e) => setTicker(e.target.value.toUpperCase())}
            />
          </div>

          {/* Quantity + Price */}
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1.5">
              <Label htmlFor="qty">Quantity</Label>
              <Input
                id="qty"
                type="number"
                min="1"
                placeholder="50"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="price">Price (₹)</Label>
              <Input
                id="price"
                type="number"
                min="0.01"
                step="0.01"
                placeholder="1280.50"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
              />
            </div>
          </div>

          {/* Total */}
          {totalValue > 0 && (
            <div className="text-sm text-muted-foreground bg-muted/50 rounded-md px-3 py-2">
              Total Value: <span className="font-semibold text-foreground">
                ₹{totalValue.toLocaleString("en-IN", { minimumFractionDigits: 2 })}
              </span>
            </div>
          )}

          {/* Date */}
          <div className="space-y-1.5">
            <Label htmlFor="date">Transaction Date</Label>
            <Input
              id="date"
              type="date"
              value={txnDate}
              onChange={(e) => setTxnDate(e.target.value)}
            />
          </div>

          {/* Sector (BUY only) */}
          {txnType === "BUY" && (
            <div className="space-y-1.5">
              <Label>Sector (optional)</Label>
              <Select value={sector} onValueChange={setSector}>
                <SelectTrigger>
                  <SelectValue placeholder="Select sector..." />
                </SelectTrigger>
                <SelectContent>
                  {SECTOR_OPTIONS.map((s) => (
                    <SelectItem key={s} value={s}>{s}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          {/* Notes */}
          <div className="space-y-1.5">
            <Label htmlFor="notes">Notes (optional)</Label>
            <Textarea
              id="notes"
              placeholder="Reason for trade..."
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={2}
            />
          </div>

          {/* Error */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
              {error}
            </div>
          )}

          {/* Submit */}
          <Button
            className={`w-full ${txnType === "BUY" ? "bg-emerald-600 hover:bg-emerald-700" : "bg-red-600 hover:bg-red-700"}`}
            onClick={handleSubmit}
            disabled={loading}
          >
            {loading ? "Processing..." : `${txnType === "BUY" ? "Buy" : "Sell"} ${ticker || "Stock"}`}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
