"use client";

import { useState, useRef } from "react";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Upload, FileSpreadsheet, CheckCircle, AlertCircle } from "lucide-react";
import { uploadPmsFiles } from "@/lib/pms-api";

interface PmsUploadDialogProps {
  portfolioId: number;
  onUploaded: () => void;
}

export function PmsUploadDialog({ portfolioId, onUploaded }: PmsUploadDialogProps) {
  const [open, setOpen] = useState(false);
  const [navFile, setNavFile] = useState<File | null>(null);
  const [txnFile, setTxnFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState<{
    success: boolean;
    message: string;
  } | null>(null);

  const navRef = useRef<HTMLInputElement>(null);
  const txnRef = useRef<HTMLInputElement>(null);

  const handleUpload = async () => {
    if (!navFile) return;
    setUploading(true);
    setResult(null);

    try {
      const res = await uploadPmsFiles(portfolioId, navFile, txnFile || undefined);
      setResult({
        success: true,
        message: `Imported ${res.new_nav_records} NAV records` +
          (res.new_transactions ? `, ${res.new_transactions} transactions` : "") +
          (res.date_range?.start ? ` (${res.date_range.start} to ${res.date_range.end})` : ""),
      });
      onUploaded();
    } catch (err) {
      setResult({
        success: false,
        message: err instanceof Error ? err.message : "Upload failed",
      });
    } finally {
      setUploading(false);
    }
  };

  const handleClose = () => {
    setOpen(false);
    setNavFile(null);
    setTxnFile(null);
    setResult(null);
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className="gap-1.5 text-xs"
        onClick={() => setOpen(true)}
      >
        <Upload className="h-3.5 w-3.5" />
        Upload Data
      </Button>

      <Dialog open={open} onOpenChange={(v) => { if (!v) handleClose(); else setOpen(true); }}>
        <DialogContent className="sm:max-w-[480px]">
          <DialogHeader>
            <DialogTitle>Upload PMS Data</DialogTitle>
            <DialogDescription>
              Upload NAV report and transaction log from your PMS broker.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 pt-2">
            {/* NAV File (required) */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">
                NAV Report <span className="text-red-500">*</span>
              </label>
              <input
                ref={navRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(e) => setNavFile(e.target.files?.[0] || null)}
              />
              <button
                type="button"
                onClick={() => navRef.current?.click()}
                className="w-full border-2 border-dashed border-slate-200 rounded-lg p-4 text-center hover:border-teal-400 hover:bg-teal-50/30 transition-colors cursor-pointer"
              >
                {navFile ? (
                  <div className="flex items-center justify-center gap-2 text-teal-700">
                    <FileSpreadsheet className="h-5 w-5" />
                    <span className="text-sm font-medium">{navFile.name}</span>
                  </div>
                ) : (
                  <div className="text-slate-400">
                    <FileSpreadsheet className="h-8 w-8 mx-auto mb-1" />
                    <p className="text-sm">Click to select NAV report (.xlsx)</p>
                  </div>
                )}
              </button>
            </div>

            {/* Transaction File (optional) */}
            <div>
              <label className="text-sm font-medium text-slate-700 mb-1.5 block">
                Transaction Log <span className="text-slate-400 font-normal">(optional)</span>
              </label>
              <input
                ref={txnRef}
                type="file"
                accept=".xlsx"
                className="hidden"
                onChange={(e) => setTxnFile(e.target.files?.[0] || null)}
              />
              <button
                type="button"
                onClick={() => txnRef.current?.click()}
                className="w-full border-2 border-dashed border-slate-200 rounded-lg p-3 text-center hover:border-teal-400 hover:bg-teal-50/30 transition-colors cursor-pointer"
              >
                {txnFile ? (
                  <div className="flex items-center justify-center gap-2 text-teal-700">
                    <FileSpreadsheet className="h-4 w-4" />
                    <span className="text-sm font-medium">{txnFile.name}</span>
                  </div>
                ) : (
                  <p className="text-sm text-slate-400">Click to select transaction log (.xlsx)</p>
                )}
              </button>
            </div>

            {/* Result message */}
            {result && (
              <div className={`flex items-start gap-2 p-3 rounded-lg text-sm ${
                result.success
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-red-50 text-red-700"
              }`}>
                {result.success
                  ? <CheckCircle className="h-4 w-4 mt-0.5 shrink-0" />
                  : <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
                }
                <span>{result.message}</span>
              </div>
            )}

            {/* Actions */}
            <div className="flex justify-end gap-2 pt-2">
              <Button variant="outline" onClick={handleClose} disabled={uploading}>
                {result?.success ? "Close" : "Cancel"}
              </Button>
              {!result?.success && (
                <Button
                  onClick={handleUpload}
                  disabled={!navFile || uploading}
                  className="bg-teal-600 text-white hover:bg-teal-700"
                >
                  {uploading ? "Uploading..." : "Upload"}
                </Button>
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </>
  );
}
