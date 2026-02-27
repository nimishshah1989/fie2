import { cn } from "@/lib/utils";

const config = {
  BULLISH: {
    classes: "bg-emerald-50 text-emerald-700 border-emerald-200",
    label: "\u25B2 Bull",
  },
  BEARISH: {
    classes: "bg-red-50 text-red-700 border-red-200",
    label: "\u25BC Bear",
  },
  NEUTRAL: {
    classes: "bg-slate-50 text-slate-600 border-slate-200",
    label: "\u25CF Neutral",
  },
} as const;

interface SignalChipProps {
  signal: "BULLISH" | "BEARISH" | "NEUTRAL";
}

export function SignalChip({ signal }: SignalChipProps) {
  const { classes, label } = config[signal];
  return (
    <span
      className={cn(
        "inline-flex items-center text-xs font-medium rounded-full px-2 py-0.5 border",
        classes
      )}
    >
      {label}
    </span>
  );
}
