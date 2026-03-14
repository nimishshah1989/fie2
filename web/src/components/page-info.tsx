"use client";

import { useState } from "react";
import { Info, X } from "lucide-react";

interface PageInfoProps {
  children: React.ReactNode;
}

export function PageInfo({ children }: PageInfoProps) {
  const [open, setOpen] = useState(false);

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="inline-flex items-center gap-1.5 text-xs text-muted-foreground hover:text-primary transition-colors"
      >
        <Info className="size-3.5" />
        <span>How this works</span>
      </button>
    );
  }

  return (
    <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-xs text-blue-800 leading-relaxed relative">
      <button
        onClick={() => setOpen(false)}
        className="absolute top-3 right-3 text-blue-400 hover:text-blue-600"
      >
        <X className="size-4" />
      </button>
      {children}
    </div>
  );
}
