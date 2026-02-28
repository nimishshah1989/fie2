import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatPrice(v: number | null | undefined): string {
  if (v == null) return "—";
  if (v > 100) return `₹${v.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
  return v.toFixed(2);
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

/** Maps period keys (lowercase) to calendar days — mirrors server.py period_map */
export const PERIOD_DAYS: Record<string, number> = {
  "1d": 1,
  "1w": 7,
  "1m": 30,
  "3m": 90,
  "6m": 180,
  "12m": 365,
};

/** Derive signal from the period-relative performance ratio */
export function getRelativeSignal(ratio: number | null): string {
  if (ratio == null) return "NEUTRAL";
  if (ratio > 1.05) return "STRONG OW";
  if (ratio > 1.0) return "OVERWEIGHT";
  if (ratio < 0.95) return "STRONG UW";
  if (ratio < 1.0) return "UNDERWEIGHT";
  return "NEUTRAL";
}

/** Annualize a period return: (ratio ^ (365/days)) - 1, returned as % */
export function computeXirr(ratio: number | null, periodDays: number): number | null {
  if (ratio == null || ratio <= 0 || periodDays <= 0) return null;
  return (Math.pow(ratio, 365 / periodDays) - 1) * 100;
}

/** Format a ratio to 4 decimal places */
export function formatRatio(v: number | null | undefined): string {
  if (v == null) return "---";
  return v.toFixed(4);
}
