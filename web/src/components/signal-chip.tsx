import { cn } from "@/lib/utils";

const config: Record<string, { classes: string; label: string }> = {
  BULLISH: {
    classes: "bg-emerald-50 text-emerald-700 border-emerald-200",
    label: "\u25B2 Bull",
  },
  BEARISH: {
    classes: "bg-red-50 text-red-700 border-red-200",
    label: "\u25BC Bear",
  },
  "STRONG OW": {
    classes: "bg-emerald-100 text-emerald-800 border-emerald-300",
    label: "\u25B2 Strong OW",
  },
  OVERWEIGHT: {
    classes: "bg-emerald-50 text-emerald-700 border-emerald-200",
    label: "\u25B2 OW",
  },
  "STRONG UW": {
    classes: "bg-red-100 text-red-800 border-red-300",
    label: "\u25BC Strong UW",
  },
  UNDERWEIGHT: {
    classes: "bg-red-50 text-red-700 border-red-200",
    label: "\u25BC UW",
  },
  BASE: {
    classes: "bg-blue-50 text-blue-700 border-blue-200",
    label: "\u25CF Base",
  },
};

interface SignalChipProps {
  signal: string;
}

export function SignalChip({ signal }: SignalChipProps) {
  if (signal === "NEUTRAL") return null;
  const entry = config[signal];
  if (!entry) return null;
  return (
    <span
      className={cn(
        "inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5 border",
        entry.classes
      )}
    >
      {entry.label}
    </span>
  );
}
