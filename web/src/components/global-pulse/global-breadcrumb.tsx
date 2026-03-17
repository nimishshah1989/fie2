"use client";

import { ChevronRight, Globe } from "lucide-react";

interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
}

interface GlobalBreadcrumbProps {
  items: BreadcrumbItem[];
}

export function GlobalBreadcrumb({ items }: GlobalBreadcrumbProps) {
  return (
    <nav className="flex items-center gap-1 text-sm text-muted-foreground">
      <Globe className="size-4 text-teal-600 shrink-0" />
      {items.map((item, i) => (
        <span key={i} className="flex items-center gap-1">
          {i > 0 && <ChevronRight className="size-3 shrink-0" />}
          {item.onClick ? (
            <button
              type="button"
              onClick={item.onClick}
              className="hover:text-teal-600 transition-colors"
            >
              {item.label}
            </button>
          ) : (
            <span className="text-foreground font-medium">{item.label}</span>
          )}
        </span>
      ))}
    </nav>
  );
}
