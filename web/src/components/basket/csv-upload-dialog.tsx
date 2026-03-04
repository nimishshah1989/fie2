"use client";

import { useState, useRef } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Upload, CheckCircle2, AlertTriangle } from "lucide-react";
import { uploadBasketCSV } from "@/lib/basket-api";
import type { CsvUploadResponse } from "@/lib/basket-types";

interface CsvUploadDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function CsvUploadDialog({ open, onOpenChange, onSuccess }: CsvUploadDialogProps) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<CsvUploadResponse | null>(null);
  const [error, setError] = useState("");

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    setResult(null);
    setError("");
  }

  async function handleUpload() {
    if (!file) return;
    setUploading(true);
    setError("");
    setResult(null);

    try {
      const res = await uploadBasketCSV(file);
      setResult(res);
      // Auto-refresh parent if any baskets were created
      if (res.results?.some((r) => r.success)) {
        onSuccess();
      }
    } catch {
      setError("Upload failed — please try again");
    } finally {
      setUploading(false);
    }
  }

  function handleClose(open: boolean) {
    if (!open) {
      setFile(null);
      setResult(null);
      setError("");
    }
    onOpenChange(open);
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Upload Baskets CSV</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-2">
          {/* Format hint */}
          <div className="rounded-lg border bg-muted/50 p-3 text-xs text-muted-foreground">
            <p className="font-semibold mb-1">CSV Format:</p>
            <code className="block bg-background rounded px-2 py-1 text-[11px] font-mono">
              basket_name, ticker, company_name, weight(%), price, quantity
            </code>
            <p className="mt-1">
              Group rows by basket_name. Weights per basket must sum to ~100%.
            </p>
            <p className="mt-0.5">
              Price &amp; quantity are optional. If provided, portfolio value = sum(price × qty).
            </p>
          </div>

          {/* File picker */}
          <div className="flex items-center gap-3">
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              onChange={handleFileChange}
              className="hidden"
            />
            <Button
              variant="outline"
              onClick={() => fileRef.current?.click()}
              className="flex-1"
            >
              <Upload className="h-4 w-4 mr-2" />
              {file ? file.name : "Choose CSV file..."}
            </Button>
            <Button
              onClick={handleUpload}
              disabled={!file || uploading}
            >
              {uploading ? "Uploading..." : "Upload"}
            </Button>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
              {error}
            </div>
          )}

          {/* Results */}
          {result && (
            <div className="space-y-2">
              <p className="text-sm text-muted-foreground">
                Parsed {result.rows_parsed} rows, found {result.baskets_found} basket(s):
              </p>
              {result.results.map((r, i) => (
                <div
                  key={i}
                  className={`flex items-start gap-2 rounded-lg border p-3 text-sm ${
                    r.success
                      ? "border-emerald-200 bg-emerald-50"
                      : "border-red-200 bg-red-50"
                  }`}
                >
                  {r.success ? (
                    <CheckCircle2 className="h-4 w-4 text-emerald-600 mt-0.5 shrink-0" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-red-600 mt-0.5 shrink-0" />
                  )}
                  <div>
                    <span className="font-medium">{r.basket_name}</span>
                    {r.success ? (
                      <span className="text-emerald-700 ml-1">
                        — Created ({r.num_constituents} stocks)
                      </span>
                    ) : (
                      <span className="text-red-700 ml-1">— {r.error}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Close after results */}
          {result && (
            <div className="flex justify-end">
              <Button variant="outline" onClick={() => handleClose(false)}>
                Done
              </Button>
            </div>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
