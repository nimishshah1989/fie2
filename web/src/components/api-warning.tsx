"use client";

import { AlertTriangle } from "lucide-react";
import { useStatus } from "@/hooks/use-status";

export function ApiWarning() {
  const { analysisEnabled } = useStatus();

  if (analysisEnabled) return null;

  return (
    <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 text-amber-800 rounded-lg px-4 py-3 text-sm">
      <AlertTriangle className="h-4 w-4 shrink-0" />
      <span>Analysis is currently disabled on the server.</span>
    </div>
  );
}
