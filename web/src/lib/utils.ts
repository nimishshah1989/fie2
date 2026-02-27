import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v > 100) return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return v.toFixed(5);
}

export function formatVolume(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v >= 1e6) return `${(v / 1e6).toFixed(1)}M`;
  if (v >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return v.toFixed(0);
}

export function formatTimestamp(ts: string | null | undefined): string {
  if (!ts) return "—";
  try {
    const dt = new Date(ts);
    return dt.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" }) +
      ", " + dt.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", hour12: true });
  } catch { return ts; }
}

export function formatPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}
