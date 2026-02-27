"use client";

import { useState, useRef, useCallback, useEffect } from "react";
import type { Alert, ActionRequest, AlertAction } from "@/lib/types";
import { postAction, updateAction } from "@/lib/api";
import { ACTION_OPTIONS, PRIORITY_OPTIONS } from "@/lib/constants";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Upload, Loader2 } from "lucide-react";

interface FmActionDialogProps {
  alert: Alert | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSubmitted: () => void;
  mode?: "create" | "edit";
  initialData?: AlertAction | null;
}

export function FmActionDialog({
  alert,
  open,
  onOpenChange,
  onSubmitted,
  mode = "create",
  initialData,
}: FmActionDialogProps) {
  const [action, setAction] = useState<string>("");
  const [priority, setPriority] = useState<string>("");
  const [fmNotes, setFmNotes] = useState<string>("");
  const [chartBase64, setChartBase64] = useState<string>("");
  const [chartFileName, setChartFileName] = useState<string>("");
  const [ratioLong, setRatioLong] = useState<string>("");
  const [ratioShort, setRatioShort] = useState<string>("");
  const [entryPriceLow, setEntryPriceLow] = useState<string>("");
  const [entryPriceHigh, setEntryPriceHigh] = useState<string>("");
  const [stopLoss, setStopLoss] = useState<string>("");
  const [targetPrice, setTargetPrice] = useState<string>("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string>("");

  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetForm = useCallback(() => {
    setAction("");
    setPriority("");
    setFmNotes("");
    setChartBase64("");
    setChartFileName("");
    setRatioLong("");
    setRatioShort("");
    setEntryPriceLow("");
    setEntryPriceHigh("");
    setStopLoss("");
    setTargetPrice("");
    setSubmitting(false);
    setError("");
  }, []);

  // Pre-fill form in edit mode
  useEffect(() => {
    if (mode === "edit" && initialData && open) {
      setAction(initialData.action_call ?? "");
      setPriority(initialData.priority ?? "");
      setFmNotes(initialData.fm_notes ?? "");
      setRatioLong(initialData.ratio_long ?? "");
      setRatioShort(initialData.ratio_short ?? "");
      setEntryPriceLow(initialData.entry_price_low != null ? String(initialData.entry_price_low) : "");
      setEntryPriceHigh(initialData.entry_price_high != null ? String(initialData.entry_price_high) : "");
      setStopLoss(initialData.stop_loss != null ? String(initialData.stop_loss) : "");
      setTargetPrice(initialData.target_price != null ? String(initialData.target_price) : "");
    }
  }, [mode, initialData, open]);

  const handleOpenChange = useCallback(
    (nextOpen: boolean) => {
      if (!nextOpen) {
        resetForm();
      }
      onOpenChange(nextOpen);
    },
    [onOpenChange, resetForm]
  );

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (!file) return;

      setChartFileName(file.name);

      const reader = new FileReader();
      reader.onload = () => {
        const result = reader.result as string;
        // Strip the "data:image/...;base64," prefix
        const base64 = result.split(",")[1] ?? "";
        setChartBase64(base64);
      };
      reader.readAsDataURL(file);
    },
    []
  );

  const handleSubmit = useCallback(async () => {
    if (!alert) return;

    if (!action) {
      setError("Please select an action.");
      return;
    }

    if (!priority) {
      setError("Please select a priority.");
      return;
    }

    if (action === "RATIO" && (!ratioLong.trim() || !ratioShort.trim())) {
      setError("Please enter both long and short tickers for a ratio trade.");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      // Parse optional numeric fields
      const parsedEntryLow = entryPriceLow ? parseFloat(entryPriceLow) : undefined;
      const parsedEntryHigh = entryPriceHigh ? parseFloat(entryPriceHigh) : undefined;
      const parsedSL = stopLoss ? parseFloat(stopLoss) : undefined;
      const parsedTP = targetPrice ? parseFloat(targetPrice) : undefined;

      if (mode === "edit") {
        // Edit mode: call updateAction
        const editPayload: Record<string, unknown> = {
          action_call: action,
          priority,
          fm_notes: fmNotes.trim() || null,
          entry_price_low: parsedEntryLow ?? null,
          entry_price_high: parsedEntryHigh ?? null,
          stop_loss: parsedSL ?? null,
          target_price: parsedTP ?? null,
        };

        const result = await updateAction(alert.id, editPayload);

        if (result.success) {
          resetForm();
          onSubmitted();
        } else {
          setError(result.error ?? "Failed to update action. Please try again.");
        }
      } else {
        // Create mode: call postAction
        const payload: ActionRequest = {
          alert_id: alert.id,
          decision: "APPROVED",
          action_call: action,
          is_ratio: action === "RATIO",
          priority,
          fm_notes: fmNotes.trim() || undefined,
          entry_price_low: parsedEntryLow,
          entry_price_high: parsedEntryHigh,
          stop_loss: parsedSL,
          target_price: parsedTP,
        };

        if (action === "RATIO") {
          payload.ratio_long = ratioLong.trim();
          payload.ratio_short = ratioShort.trim();
        }

        if (chartBase64) {
          payload.chart_image_b64 = chartBase64;
        }

        const result = await postAction(payload);

        if (result.success) {
          resetForm();
          onSubmitted();
        } else {
          setError(result.error ?? "Failed to submit action. Please try again.");
        }
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "An unexpected error occurred."
      );
    } finally {
      setSubmitting(false);
    }
  }, [
    alert,
    action,
    priority,
    fmNotes,
    chartBase64,
    ratioLong,
    ratioShort,
    entryPriceLow,
    entryPriceHigh,
    stopLoss,
    targetPrice,
    mode,
    resetForm,
    onSubmitted,
  ]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>
            {mode === "edit" ? "Edit Action" : "FM Action"} — {alert?.ticker ?? "Alert"}
          </DialogTitle>
          <DialogDescription>
            {mode === "edit" ? "Update the action for" : "Submit your decision for"}{" "}
            <span className="font-medium text-foreground">
              {alert?.alert_name}
            </span>
          </DialogDescription>
        </DialogHeader>

        <div className="grid gap-5 py-2">
          {/* Action Select */}
          <div className="grid gap-2">
            <Label htmlFor="fm-action">Action</Label>
            <Select value={action} onValueChange={setAction}>
              <SelectTrigger id="fm-action" className="w-full">
                <SelectValue placeholder="Select action..." />
              </SelectTrigger>
              <SelectContent>
                {ACTION_OPTIONS.map((opt) => (
                  <SelectItem key={opt} value={opt}>
                    {opt}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Priority Select */}
          <div className="grid gap-2">
            <Label htmlFor="fm-priority">Priority</Label>
            <Select value={priority} onValueChange={setPriority}>
              <SelectTrigger id="fm-priority" className="w-full">
                <SelectValue placeholder="Select priority..." />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Ratio Fields — conditional */}
          {action === "RATIO" && (
            <div className="grid grid-cols-2 gap-4">
              <div className="grid gap-2">
                <Label htmlFor="fm-ratio-long">Long Ticker</Label>
                <Input
                  id="fm-ratio-long"
                  placeholder="e.g. NIFTY IT"
                  value={ratioLong}
                  onChange={(e) => setRatioLong(e.target.value)}
                />
              </div>
              <div className="grid gap-2">
                <Label htmlFor="fm-ratio-short">Short Ticker</Label>
                <Input
                  id="fm-ratio-short"
                  placeholder="e.g. NIFTY BANK"
                  value={ratioShort}
                  onChange={(e) => setRatioShort(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Trade Parameters */}
          <div className="grid gap-3">
            <Label className="text-sm font-medium">Trade Parameters</Label>
            <div className="grid grid-cols-2 gap-3">
              <div className="grid gap-1.5">
                <Label htmlFor="fm-entry-low" className="text-xs text-muted-foreground">
                  Entry Price (Low)
                </Label>
                <Input
                  id="fm-entry-low"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 450"
                  value={entryPriceLow}
                  onChange={(e) => setEntryPriceLow(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="fm-entry-high" className="text-xs text-muted-foreground">
                  Entry Price (High)
                </Label>
                <Input
                  id="fm-entry-high"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 500"
                  value={entryPriceHigh}
                  onChange={(e) => setEntryPriceHigh(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="fm-stop-loss" className="text-xs text-muted-foreground">
                  Stop Loss
                </Label>
                <Input
                  id="fm-stop-loss"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 420"
                  value={stopLoss}
                  onChange={(e) => setStopLoss(e.target.value)}
                />
              </div>
              <div className="grid gap-1.5">
                <Label htmlFor="fm-target" className="text-xs text-muted-foreground">
                  Target Price
                </Label>
                <Input
                  id="fm-target"
                  type="number"
                  step="0.01"
                  placeholder="e.g. 600"
                  value={targetPrice}
                  onChange={(e) => setTargetPrice(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* FM Commentary */}
          <div className="grid gap-2">
            <Label htmlFor="fm-notes">FM Commentary</Label>
            <Textarea
              id="fm-notes"
              placeholder="Add your analysis notes..."
              value={fmNotes}
              onChange={(e) => setFmNotes(e.target.value)}
              className="min-h-[100px]"
            />
          </div>

          {/* Chart Upload */}
          <div className="grid gap-2">
            <Label>Chart Upload</Label>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
            <div className="flex items-center gap-3">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleFileSelect}
              >
                <Upload className="h-3.5 w-3.5" />
                Choose Image
              </Button>
              {chartFileName && (
                <span className="text-sm text-muted-foreground truncate max-w-[300px]">
                  {chartFileName}
                </span>
              )}
            </div>
          </div>

          {/* Error message */}
          {error && (
            <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {error}
            </div>
          )}
        </div>

        {/* Footer Buttons */}
        <div className="flex items-center justify-end gap-3 pt-2">
          <Button
            variant="outline"
            onClick={() => handleOpenChange(false)}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            className="bg-emerald-600 hover:bg-emerald-700 text-white"
            onClick={handleSubmit}
            disabled={submitting}
          >
            {submitting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                {mode === "edit" ? "Saving..." : "Submitting..."}
              </>
            ) : (
              mode === "edit" ? "Save Changes" : "Submit"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
