"use client";

import type { BasketLiveItem } from "@/lib/basket-types";
import { BasketRichCard } from "./basket-rich-card";

interface BasketCardGridProps {
  baskets: BasketLiveItem[];
  period: string;
  selectedId: number | null;
  onSelect: (id: number) => void;
}

export function BasketCardGrid({ baskets, period, selectedId, onSelect }: BasketCardGridProps) {
  if (baskets.length === 0) return null;

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {baskets.map((basket) => (
        <BasketRichCard
          key={basket.id}
          basket={basket}
          period={period}
          isSelected={selectedId === basket.id}
          onClick={() => onSelect(basket.id)}
        />
      ))}
    </div>
  );
}
