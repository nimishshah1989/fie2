"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPrice, formatPct, cn } from "@/lib/utils";
import type { LiveIndex } from "@/lib/types";
import { TrendingDown } from "lucide-react";

interface FixedIncomeTableProps {
  indices: LiveIndex[];
}

/** Color class for a return value: emerald for positive, red for negative, slate for null */
function returnColor(v: number | null | undefined): string {
  if (v == null) return "text-slate-400";
  return v >= 0 ? "text-emerald-600" : "text-red-600";
}

/** Render a return cell value with consistent formatting */
function ReturnCell({ value }: { value: number | null | undefined }) {
  return (
    <span className={cn("font-mono tabular-nums text-sm", returnColor(value))}>
      {value != null ? formatPct(value) : "---"}
    </span>
  );
}

export function FixedIncomeTable({ indices }: FixedIncomeTableProps) {
  if (indices.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-slate-200 p-12 text-center">
        <TrendingDown className="mx-auto h-10 w-10 text-slate-300 mb-3" />
        <p className="text-sm font-medium text-slate-500">
          No fixed income data available yet.
        </p>
        <p className="text-xs text-slate-400 mt-1">
          Data will appear once the daily backfill completes.
        </p>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="px-4 pt-3">
        <p className="text-xs text-slate-400 italic mb-3">
          Fixed income index data is updated daily after market close. Historical
          data available from backfill date.
        </p>
      </div>
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-slate-50/60">
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                Index Name
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                Last Price
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                Change %
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                1W
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                1M
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                3M
              </TableHead>
              <TableHead className="text-xs font-semibold text-slate-400 uppercase tracking-wider text-right">
                1Y
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {indices.map((idx) => {
              const name = idx.nse_name || idx.index_name;
              const pctChange = idx.percentChange ?? null;

              return (
                <TableRow key={name}>
                  <TableCell className="font-medium text-sm text-slate-700">
                    {name}
                  </TableCell>
                  <TableCell className="text-right font-mono tabular-nums text-sm">
                    {formatPrice(idx.last)}
                  </TableCell>
                  <TableCell className={cn("text-right font-mono tabular-nums text-sm", returnColor(pctChange))}>
                    {pctChange != null ? formatPct(pctChange) : "---"}
                  </TableCell>
                  <TableCell className="text-right">
                    <ReturnCell value={idx.index_returns?.["1w"]} />
                  </TableCell>
                  <TableCell className="text-right">
                    <ReturnCell value={idx.index_returns?.["1m"]} />
                  </TableCell>
                  <TableCell className="text-right">
                    <ReturnCell value={idx.index_returns?.["3m"]} />
                  </TableCell>
                  <TableCell className="text-right">
                    <ReturnCell value={idx.index_returns?.["12m"]} />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
