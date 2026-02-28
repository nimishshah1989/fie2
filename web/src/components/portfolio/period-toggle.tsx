"use client";

import { Button } from "@/components/ui/button";

const PERIODS = ["1M", "3M", "6M", "1Y", "YTD", "ALL"];

interface PeriodToggleProps {
  selected: string;
  onChange: (period: string) => void;
}

export function PeriodToggle({ selected, onChange }: PeriodToggleProps) {
  return (
    <div className="flex gap-1">
      {PERIODS.map((p) => (
        <Button
          key={p}
          variant={selected === p ? "default" : "outline"}
          size="sm"
          className="text-xs h-7 px-3"
          onClick={() => onChange(p)}
        >
          {p}
        </Button>
      ))}
    </div>
  );
}
