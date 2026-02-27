"use client";

import { useState, useMemo } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SignalChip } from "@/components/signal-chip";
import {
  formatPrice,
  formatPct,
  formatRatio,
  cn,
  getRelativeSignal,
} from "@/lib/utils";
import { getSector, SECTOR_ORDER, TOP_25_SET } from "@/lib/constants";
import type { LiveIndex } from "@/lib/types";
import { ChevronUp, ChevronDown, ChevronsUpDown } from "lucide-react";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";

/** Small (i) icon with a portal-based tooltip (not clipped by overflow) */
function InfoTip({ text }: { text: string }) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <span className="inline-flex items-center justify-center size-3.5 rounded-full bg-muted-foreground/20 text-[9px] font-bold leading-none text-muted-foreground ml-1 cursor-help">
          i
        </span>
      </TooltipTrigger>
      <TooltipContent
        side="top"
        sideOffset={6}
        className="max-w-64 whitespace-pre-line text-[11px] leading-snug font-normal normal-case tracking-normal"
      >
        {text}
      </TooltipContent>
    </Tooltip>
  );
}

type SortField = "indexReturn" | "ratioReturn" | null;
type SortDir = "asc" | "desc";

interface IndexTableProps {
  indices: LiveIndex[];
  period: string;
  timestamp?: string;
}

interface SectorGroup {
  sector: string;
  items: LiveIndex[];
}

/** Sort chevron indicator */
function SortIcon({ field, sortField, sortDir }: { field: SortField; sortField: SortField; sortDir: SortDir }) {
  if (sortField !== field) {
    return <ChevronsUpDown className="inline h-3 w-3 ml-0.5 opacity-40" />;
  }
  return sortDir === "asc"
    ? <ChevronUp className="inline h-3 w-3 ml-0.5" />
    : <ChevronDown className="inline h-3 w-3 ml-0.5" />;
}

export function IndexTable({ indices, period, timestamp }: IndexTableProps) {
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  const pk = period.toLowerCase();

  function handleSort(field: SortField) {
    if (sortField === field) {
      if (sortDir === "desc") {
        setSortDir("asc");
      } else {
        // Third click: reset to no sort
        setSortField(null);
        setSortDir("desc");
      }
    } else {
      setSortField(field);
      setSortDir("desc");
    }
  }

  // Build sector groups for default (no sort) view
  const groups = useMemo<SectorGroup[]>(() => {
    const sectorMap = new Map<string, LiveIndex[]>();
    for (const idx of indices) {
      const name = idx.nse_name || idx.index_name;
      const sector = getSector(name);
      if (!sectorMap.has(sector)) {
        sectorMap.set(sector, []);
      }
      sectorMap.get(sector)!.push(idx);
    }

    const result: SectorGroup[] = [];
    for (const sector of SECTOR_ORDER) {
      const items = sectorMap.get(sector);
      if (items && items.length > 0) {
        result.push({ sector, items });
      }
    }
    for (const [sector, items] of sectorMap) {
      if (!SECTOR_ORDER.includes(sector) && items.length > 0) {
        result.push({ sector, items });
      }
    }
    return result;
  }, [indices]);

  // Sorted flat list when sort is active
  const sortedFlat = useMemo(() => {
    if (!sortField) return null;

    const arr = [...indices];
    arr.sort((a, b) => {
      let va: number | null = null;
      let vb: number | null = null;

      if (sortField === "indexReturn") {
        va = a.index_returns?.[pk] ?? null;
        vb = b.index_returns?.[pk] ?? null;
      } else if (sortField === "ratioReturn") {
        va = a.ratio_returns?.[pk] ?? null;
        vb = b.ratio_returns?.[pk] ?? null;
      }

      // Nulls to bottom
      if (va == null && vb == null) return 0;
      if (va == null) return 1;
      if (vb == null) return -1;

      return sortDir === "desc" ? vb - va : va - vb;
    });

    return arr;
  }, [indices, sortField, sortDir, pk]);

  return (
    <div className="rounded-lg border bg-card">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30">
              <TableHead>Index Name</TableHead>
              <TableHead className="text-right">
                Last Price
                {timestamp && (
                  <span className="block text-[10px] font-normal text-muted-foreground/70">
                    {timestamp}
                  </span>
                )}
              </TableHead>
              <TableHead className="text-right">
                Change %
                <InfoTip text={"Today's daily price change from NSE.\n= (Last \u2212 Prev Close) / Prev Close"} />
              </TableHead>
              <TableHead
                className="text-right cursor-pointer select-none hover:bg-muted/50 transition-colors"
                onClick={() => handleSort("indexReturn")}
              >
                Index Ret ({period})
                <SortIcon field="indexReturn" sortField={sortField} sortDir={sortDir} />
                <InfoTip text={"The index's own absolute return over the period.\n= (Price today / Price old \u2212 1) \u00D7 100\nThis is the index's standalone performance, not relative to the base."} />
              </TableHead>
              <TableHead className="text-right">
                Ratio ({period})
                <InfoTip text={"Relative performance vs base index over the selected period.\n= (Index today / Index old) \u00F7 (Base today / Base old)\n> 1 = outperformed base\n< 1 = underperformed base"} />
              </TableHead>
              <TableHead className="text-center">
                Signal
                <InfoTip text={"Relative signal based on Ratio value:\n\u2022 Strong OW: Ratio > 1.05 (index strongly outperforming base)\n\u2022 Overweight: Ratio > 1.00 (index mildly outperforming)\n\u2022 Neutral: Ratio = 1.00\n\u2022 Underweight: Ratio < 1.00 (index mildly underperforming)\n\u2022 Strong UW: Ratio < 0.95 (index strongly underperforming)\n\u2022 BASE: this is the base index itself"} />
              </TableHead>
              <TableHead
                className="text-right cursor-pointer select-none hover:bg-muted/50 transition-colors"
                onClick={() => handleSort("ratioReturn")}
              >
                Ratio Ret ({period})
                <SortIcon field="ratioReturn" sortField={sortField} sortDir={sortDir} />
                <InfoTip text={"Excess return over the base index.\n= (Ratio \u2212 1) \u00D7 100\nPositive = outperformed base index.\nNegative = underperformed base index."} />
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortField && sortedFlat ? (
              // Sorted: flat list, no sector headers
              sortedFlat.map((idx) => (
                <IndexRow key={idx.nse_name || idx.index_name} idx={idx} pk={pk} />
              ))
            ) : (
              // Default: sector-grouped
              groups.map((group) => (
                <SectorSection
                  key={group.sector}
                  sector={group.sector}
                  items={group.items}
                  pk={pk}
                />
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

function SectorSection({
  sector,
  items,
  pk,
}: {
  sector: string;
  items: LiveIndex[];
  pk: string;
}) {
  return (
    <>
      {/* Sector header row */}
      <TableRow className="bg-muted/50 hover:bg-muted/50">
        <TableCell colSpan={7} className="py-2 px-3">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {sector}
          </span>
          <span className="ml-2 text-xs text-muted-foreground/70">
            ({items.length})
          </span>
        </TableCell>
      </TableRow>
      {/* Data rows */}
      {items.map((idx) => (
        <IndexRow key={idx.nse_name || idx.index_name} idx={idx} pk={pk} />
      ))}
    </>
  );
}

/** Single index row — columns: Name, Last, Change%, IndexRet, Ratio, Signal, RatioRet */
function IndexRow({ idx, pk }: { idx: LiveIndex; pk: string }) {
  const name = idx.nse_name || idx.index_name;
  const isTop25 = TOP_25_SET.has(name);
  const pctChange = idx.percentChange ?? null;
  const ratioReturn = idx.ratio_returns?.[pk] ?? null;
  const indexReturn = idx.index_returns?.[pk] ?? null;

  // Compute period-relative ratio from ratio_returns
  const relRatio = ratioReturn != null ? 1 + ratioReturn / 100 : null;
  const isBase = idx.signal === "BASE";
  const signal = isBase ? "BASE" : getRelativeSignal(relRatio);

  return (
    <TableRow
      id={`idx-${name.replace(/\s+/g, "-")}`}
      className={cn(isTop25 && "bg-primary/5")}
    >
      <TableCell className="font-medium text-sm">
        {name}
        {isTop25 && (
          <span className="ml-1.5 inline-block size-1.5 rounded-full bg-blue-500" />
        )}
      </TableCell>
      <TableCell className="text-right font-mono text-sm">
        {formatPrice(idx.last)}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm",
          pctChange != null && pctChange >= 0
            ? "text-emerald-600"
            : pctChange != null
              ? "text-red-600"
              : ""
        )}
      >
        {pctChange != null ? formatPct(pctChange) : "---"}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm",
          indexReturn != null && indexReturn >= 0
            ? "text-emerald-600"
            : indexReturn != null
              ? "text-red-600"
              : ""
        )}
      >
        {indexReturn != null ? formatPct(indexReturn) : "---"}
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm",
          relRatio != null && relRatio > 1.0
            ? "text-emerald-600"
            : relRatio != null && relRatio < 1.0
              ? "text-red-600"
              : ""
        )}
      >
        {formatRatio(relRatio)}
      </TableCell>
      <TableCell className="text-center">
        <SignalChip signal={signal} />
      </TableCell>
      <TableCell
        className={cn(
          "text-right font-mono text-sm",
          ratioReturn != null && ratioReturn >= 0
            ? "text-emerald-600"
            : ratioReturn != null
              ? "text-red-600"
              : ""
        )}
      >
        {ratioReturn != null ? formatPct(ratioReturn) : "---"}
      </TableCell>
    </TableRow>
  );
}
