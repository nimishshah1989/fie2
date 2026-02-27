import { cn } from "@/lib/utils";

const config: Record<string, { classes: string; label: string }> = {
  IMMEDIATELY: {
    classes: "bg-orange-50 text-orange-700 border-orange-200",
    label: "\uD83D\uDD34 Immediately",
  },
  WITHIN_A_WEEK: {
    classes: "bg-blue-50 text-blue-700 border-blue-200",
    label: "\uD83D\uDD35 Within a Week",
  },
  WITHIN_A_MONTH: {
    classes: "bg-purple-50 text-purple-700 border-purple-200",
    label: "\uD83D\uDFE3 Within a Month",
  },
};

interface PriorityChipProps {
  priority: string | null;
}

export function PriorityChip({ priority }: PriorityChipProps) {
  if (!priority || !config[priority]) return null;

  const { classes, label } = config[priority];
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
