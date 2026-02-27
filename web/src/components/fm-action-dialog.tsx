"use client";

import { useState, useRef, useCallback } from "react";
import type { Alert, ActionRequest } from "@/lib/types";
import { postAction } from "@/lib/api";
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
}

export function FmActionDialog({
  alert,
  open,
  onOpenChange,
  onSubmitted,
}: FmActionDialogProps) {
  const [action, setAction] = useState<string>("");
  const [priority, setPriority] = useState<string>("");
  const [fmNotes, setFmNotes] = useState<string>("");
  const [chartBase64, setChartBase64] = useState<string>("");
  const [chartFileName, setChartFileName] = useState<string>("");
  const [ratioLong, setRatioLong] = useState<string>("");
  const [ratioShort, setRatioShort] = useState<string>("");
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
    setSubmitting(false);
    setError("");
  }, []);

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
      const payload: ActionRequest = {
        alert_id: alert.id,
        decision: "APPROVED",
        action_call: action,
        is_ratio: action === "RATIO",
        priority,
        fm_notes: fmNotes.trim() || undefined,
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
    resetForm,
    onSubmitted,
  ]);

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>FM Action — {alert?.ticker ?? "Alert"}</DialogTitle>
          <DialogDescription>
            Submit your decision for{" "}
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
                Submitting...
              </>
            ) : (
              "Submit"
            )}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
