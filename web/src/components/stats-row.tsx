import { cn } from "@/lib/utils";
import { Card, CardContent } from "@/components/ui/card";

interface Stat {
  label: string;
  value: string | number;
  color?: string;
}

interface StatsRowProps {
  stats: Stat[];
}

export function StatsRow({ stats }: StatsRowProps) {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-2 sm:gap-3">
      {stats.map((stat) => (
        <Card key={stat.label} className="py-0">
          <CardContent className="p-2 sm:p-3 text-center">
            <div className={cn("text-sm sm:text-base font-bold truncate", stat.color)}>
              {stat.value}
            </div>
            <div className="text-[10px] sm:text-xs text-muted-foreground uppercase tracking-wider mt-0.5 sm:mt-1 truncate">
              {stat.label}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
