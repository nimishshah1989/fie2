"use client";

import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { Card, CardContent } from "@/components/ui/card";
import { formatPrice } from "@/lib/utils";
import type { AllocationItem } from "@/lib/portfolio-types";

const COLORS = [
  "#059669", "#2563eb", "#d97706", "#dc2626", "#7c3aed",
  "#0891b2", "#ea580c", "#4f46e5", "#16a34a", "#be123c",
  "#854d0e", "#0e7490", "#9333ea", "#c2410c",
];

interface AllocationChartProps {
  byStock: AllocationItem[];
  bySector: AllocationItem[];
}

interface TooltipPayload {
  label: string;
  value: number;
  pct: number;
}

function CustomTooltip({ active, payload }: {
  active?: boolean;
  payload?: { payload: TooltipPayload }[];
}) {
  if (!active || !payload || !payload.length) return null;
  const d = payload[0].payload;
  return (
    <div className="bg-card border border-border rounded-lg shadow-lg p-2 text-xs">
      <div className="font-semibold">{d.label}</div>
      <div className="text-muted-foreground">
        {formatPrice(d.value)} ({d.pct.toFixed(1)}%)
      </div>
    </div>
  );
}

function AllocationPie({ title, data }: { title: string; data: AllocationItem[] }) {
  if (data.length === 0) {
    return (
      <div className="flex-1">
        <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
          {title}
        </h4>
        <div className="h-48 flex items-center justify-center text-sm text-muted-foreground">
          No data
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1">
      <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wide mb-3">
        {title}
      </h4>
      <div className="flex items-center gap-3 sm:gap-4">
        <div className="w-32 h-32 sm:w-40 sm:h-40 shrink-0">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={data}
                dataKey="value"
                nameKey="label"
                cx="50%"
                cy="50%"
                innerRadius={35}
                outerRadius={65}
                paddingAngle={2}
              >
                {data.map((_, i) => (
                  <Cell key={`cell-${i}`} fill={COLORS[i % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="space-y-1.5 flex-1 min-w-0">
          {data.slice(0, 8).map((item, i) => (
            <div key={item.label} className="flex items-center gap-2 text-xs">
              <div
                className="w-2.5 h-2.5 rounded-sm shrink-0"
                style={{ backgroundColor: COLORS[i % COLORS.length] }}
              />
              <span className="truncate text-foreground">{item.label}</span>
              <span className="ml-auto font-mono text-muted-foreground shrink-0">
                {item.pct.toFixed(1)}%
              </span>
            </div>
          ))}
          {data.length > 8 && (
            <div className="text-[10px] text-muted-foreground">
              +{data.length - 8} more
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function AllocationChart({ byStock, bySector }: AllocationChartProps) {
  return (
    <Card>
      <CardContent className="p-3 sm:p-6">
        <h3 className="text-sm font-semibold text-foreground mb-3 sm:mb-4">Portfolio Allocation</h3>
        <div className="flex gap-6 sm:gap-8 flex-col md:flex-row">
          <AllocationPie title="By Stock" data={byStock} />
          <AllocationPie title="By Sector" data={bySector} />
        </div>
      </CardContent>
    </Card>
  );
}
