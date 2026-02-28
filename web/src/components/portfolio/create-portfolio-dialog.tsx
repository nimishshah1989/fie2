"use client";

import { useState, useCallback } from "react";
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
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { createPortfolio, createTransaction } from "@/lib/portfolio-api";
import { Plus, Trash2, ArrowRight, Check } from "lucide-react";

const BENCHMARK_OPTIONS = [
  "NIFTY", "SENSEX", "BANKNIFTY", "NIFTYIT",
  "NIFTYPHARMA", "NIFTYFMCG", "NIFTYAUTO", "NIFTYMETAL",
];

const INSTRUMENT_TYPES = [
  { value: "EQUITY", label: "Equity (NSE)" },
  { value: "ETF", label: "ETF" },
  { value: "MF", label: "Mutual Fund" },
];

const SECTOR_OPTIONS = [
  "Banking", "IT", "Pharma", "Energy", "Auto", "FMCG", "Metal",
  "Realty", "Infra", "Telecom", "Media", "Financial Services",
  "Cash", "ETF", "Other",
];

interface InstrumentRow {
  id: number;
  ticker: string;
  type: "EQUITY" | "ETF" | "MF";
  sector: string;
  quantity: number;
  price: number;
  date: string;
}

interface CreatePortfolioDialogProps {
  onCreated: () => void;
}

export function CreatePortfolioDialog({ onCreated }: CreatePortfolioDialogProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);

  // Step 1: Strategy setup
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [benchmark, setBenchmark] = useState("NIFTY");
  const [clientName, setClientName] = useState("");
  const [inceptionDate, setInceptionDate] = useState(new Date().toISOString().split("T")[0]);

  // Step 2: Instruments
  const [instruments, setInstruments] = useState<InstrumentRow[]>([
    { id: 1, ticker: "", type: "EQUITY", sector: "", quantity: 0, price: 0, date: new Date().toISOString().split("T")[0] },
  ]);
  const [nextId, setNextId] = useState(2);

  // Creation state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [createdPortfolioId, setCreatedPortfolioId] = useState<number | null>(null);
  const [progress, setProgress] = useState("");

  function reset() {
    setStep(1);
    setName("");
    setDescription("");
    setBenchmark("NIFTY");
    setClientName("");
    setInceptionDate(new Date().toISOString().split("T")[0]);
    setInstruments([
      { id: 1, ticker: "", type: "EQUITY", sector: "", quantity: 0, price: 0, date: new Date().toISOString().split("T")[0] },
    ]);
    setNextId(2);
    setLoading(false);
    setError("");
    setCreatedPortfolioId(null);
    setProgress("");
  }

  function addInstrumentRow() {
    setInstruments((prev) => [
      ...prev,
      { id: nextId, ticker: "", type: "EQUITY", sector: "", quantity: 0, price: 0, date: inceptionDate },
    ]);
    setNextId((n) => n + 1);
  }

  function removeInstrumentRow(id: number) {
    setInstruments((prev) => prev.filter((r) => r.id !== id));
  }

  function updateInstrument(id: number, field: keyof InstrumentRow, value: string | number) {
    setInstruments((prev) =>
      prev.map((r) => (r.id === id ? { ...r, [field]: value } : r))
    );
  }

  const validInstruments = instruments.filter(
    (r) => r.ticker.trim() && r.quantity > 0 && r.price > 0
  );

  const totalInvestment = validInstruments.reduce(
    (sum, r) => sum + r.quantity * r.price, 0
  );

  async function handleCreate() {
    setError("");
    setLoading(true);

    try {
      // Build description with client info
      const fullDesc = [
        clientName ? `Client: ${clientName}` : "",
        description,
        `Inception: ${new Date(inceptionDate).toLocaleDateString("en-IN", { day: "numeric", month: "long", year: "numeric" })}`,
      ].filter(Boolean).join(" | ");

      // Step 1: Create portfolio
      setProgress("Creating portfolio...");
      const result = await createPortfolio({
        name: name.trim(),
        description: fullDesc || undefined,
        benchmark,
      });

      if (!result.success || !result.id) {
        setError(result.error || "Failed to create portfolio");
        return;
      }

      const portfolioId = result.id;
      setCreatedPortfolioId(portfolioId);

      // Step 2: Add instruments as BUY transactions
      if (validInstruments.length > 0) {
        for (let i = 0; i < validInstruments.length; i++) {
          const inst = validInstruments[i];
          setProgress(`Adding ${inst.ticker} (${i + 1}/${validInstruments.length})...`);

          await createTransaction(portfolioId, {
            ticker: inst.ticker.trim().toUpperCase(),
            txn_type: "BUY",
            quantity: inst.quantity,
            price: inst.price,
            txn_date: inst.date || inceptionDate,
            sector: inst.sector || undefined,
          });
        }
      }

      setProgress("Done!");
      // Short delay to show success, then close
      setTimeout(() => {
        setOpen(false);
        reset();
        onCreated();
      }, 800);
    } catch {
      setError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) reset(); }}>
      <DialogTrigger asChild>
        <Button size="sm" className="gap-1.5">
          <Plus className="h-4 w-4" />
          Create Portfolio
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            Create Model Portfolio
            <div className="flex items-center gap-1 ml-auto">
              <Badge variant={step === 1 ? "default" : "outline"} className="text-[10px]">
                1. Strategy
              </Badge>
              <ArrowRight className="h-3 w-3 text-muted-foreground" />
              <Badge variant={step === 2 ? "default" : "outline"} className="text-[10px]">
                2. Instruments
              </Badge>
            </div>
          </DialogTitle>
        </DialogHeader>

        {/* ─── Step 1: Strategy Setup ─── */}
        {step === 1 && (
          <div className="space-y-4 pt-2">
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label htmlFor="name">Strategy Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g. Large Cap Growth"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="client">Client Name</Label>
                <Input
                  id="client"
                  placeholder="e.g. Bhaderesh Jhaveri"
                  value={clientName}
                  onChange={(e) => setClientName(e.target.value)}
                />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label htmlFor="description">Strategy Description</Label>
              <Textarea
                id="description"
                placeholder="Brief description of the investment strategy and thesis..."
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                rows={2}
              />
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1.5">
                <Label>Benchmark Index</Label>
                <Select value={benchmark} onValueChange={setBenchmark}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {BENCHMARK_OPTIONS.map((b) => (
                      <SelectItem key={b} value={b}>{b}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="inception">Inception Date</Label>
                <Input
                  id="inception"
                  type="date"
                  value={inceptionDate}
                  onChange={(e) => setInceptionDate(e.target.value)}
                />
              </div>
            </div>

            <Button
              className="w-full"
              onClick={() => setStep(2)}
              disabled={!name.trim()}
            >
              Next: Add Instruments
              <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </div>
        )}

        {/* ─── Step 2: Instruments ─── */}
        {step === 2 && (
          <div className="space-y-4 pt-2">
            {/* Summary header */}
            <div className="bg-muted/50 rounded-lg p-3 text-sm">
              <div className="font-semibold text-foreground">{name}</div>
              <div className="text-xs text-muted-foreground mt-0.5">
                {clientName && `${clientName} · `}Benchmark: {benchmark} · Inception: {inceptionDate}
              </div>
            </div>

            {/* Instrument Rows */}
            <div className="space-y-3">
              <div className="grid grid-cols-[1fr_80px_90px_70px_80px_80px_32px] gap-2 text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-1">
                <span>Ticker</span>
                <span>Type</span>
                <span>Sector</span>
                <span>Qty</span>
                <span>Price (\u20B9)</span>
                <span>Value</span>
                <span></span>
              </div>

              {instruments.map((inst) => (
                <div
                  key={inst.id}
                  className="grid grid-cols-[1fr_80px_90px_70px_80px_80px_32px] gap-2 items-center"
                >
                  <Input
                    placeholder="RELIANCE"
                    value={inst.ticker}
                    onChange={(e) => updateInstrument(inst.id, "ticker", e.target.value.toUpperCase())}
                    className="h-8 text-xs"
                  />
                  <Select
                    value={inst.type}
                    onValueChange={(v) => updateInstrument(inst.id, "type", v)}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {INSTRUMENT_TYPES.map((t) => (
                        <SelectItem key={t.value} value={t.value} className="text-xs">{t.label}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Select
                    value={inst.sector || "none"}
                    onValueChange={(v) => updateInstrument(inst.id, "sector", v === "none" ? "" : v)}
                  >
                    <SelectTrigger className="h-8 text-xs">
                      <SelectValue placeholder="—" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none" className="text-xs">—</SelectItem>
                      {SECTOR_OPTIONS.map((s) => (
                        <SelectItem key={s} value={s} className="text-xs">{s}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Input
                    type="number"
                    min="0"
                    placeholder="100"
                    value={inst.quantity || ""}
                    onChange={(e) => updateInstrument(inst.id, "quantity", parseInt(e.target.value) || 0)}
                    className="h-8 text-xs"
                  />
                  <Input
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="1280"
                    value={inst.price || ""}
                    onChange={(e) => updateInstrument(inst.id, "price", parseFloat(e.target.value) || 0)}
                    className="h-8 text-xs"
                  />
                  <div className="text-xs font-mono text-muted-foreground px-1">
                    {inst.quantity > 0 && inst.price > 0
                      ? `\u20B9${(inst.quantity * inst.price).toLocaleString("en-IN", { maximumFractionDigits: 0 })}`
                      : "\u2014"
                    }
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-8 w-8 p-0 text-muted-foreground hover:text-red-600"
                    onClick={() => removeInstrumentRow(inst.id)}
                    disabled={instruments.length <= 1}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              ))}
            </div>

            {/* Add row button */}
            <Button
              variant="outline"
              size="sm"
              className="w-full text-xs gap-1"
              onClick={addInstrumentRow}
            >
              <Plus className="h-3.5 w-3.5" />
              Add Instrument
            </Button>

            {/* Total */}
            {totalInvestment > 0 && (
              <div className="bg-muted/50 rounded-lg px-3 py-2 flex items-center justify-between text-sm">
                <span className="text-muted-foreground">
                  Total Investment ({validInstruments.length} instruments)
                </span>
                <span className="font-semibold font-mono text-foreground">
                  \u20B9{totalInvestment.toLocaleString("en-IN", { maximumFractionDigits: 0 })}
                </span>
              </div>
            )}

            {/* Error */}
            {error && (
              <div className="text-sm text-red-600 bg-red-50 rounded-md px-3 py-2">
                {error}
              </div>
            )}

            {/* Progress */}
            {loading && progress && (
              <div className="text-sm text-blue-600 bg-blue-50 rounded-md px-3 py-2">
                {progress}
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={() => setStep(1)}
                disabled={loading}
              >
                Back
              </Button>
              <Button
                className="flex-1 gap-1"
                onClick={handleCreate}
                disabled={loading || !name.trim()}
              >
                {loading ? (
                  progress
                ) : (
                  <>
                    <Check className="h-4 w-4" />
                    Create Portfolio{validInstruments.length > 0 ? ` (${validInstruments.length} instruments)` : ""}
                  </>
                )}
              </Button>
            </div>

            <p className="text-[10px] text-muted-foreground text-center">
              You can also create an empty portfolio and add instruments later via Add Transaction.
            </p>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
