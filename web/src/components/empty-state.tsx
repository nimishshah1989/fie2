import type { ReactNode } from "react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
}

export function EmptyState({ icon, title, description }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      {icon && (
        <div className="text-muted-foreground mb-2">{icon}</div>
      )}
      <h3 className="text-lg font-medium text-muted-foreground">{title}</h3>
      {description && (
        <p className="text-sm text-muted-foreground/70 mt-1">{description}</p>
      )}
    </div>
  );
}
