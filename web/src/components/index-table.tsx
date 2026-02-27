"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SignalChip } from "@/components/signal-chip";
import { formatPrice, formatPct, cn } from "@/lib/utils";
import { getSector, SECTOR_ORDER, TOP_25_SET } from "@/lib/constants";
import type { LiveIndex } from "@/lib/types";

interface IndexTableProps {
  indices: LiveIndex[];
  period: string;
}

interface SectorGroup {
  sector: string;
  items: LiveIndex[];
}

export function IndexTable({ indices, period }: IndexTableProps) {
  // Group indices by sector
  const sectorMap = new Map<string, LiveIndex[]>();
  for (const idx of indices) {
    const name = idx.nse_name || idx.index_name;
    const sector = getSector(name);
    if (!sectorMap.has(sector)) {
      sectorMap.set(sector, []);
    }
    sectorMap.get(sector)!.push(idx);
  }

  // Sort sector groups by SECTOR_ORDER
  const groups: SectorGroup[] = [];
  for (const sector of SECTOR_ORDER) {
    const items = sectorMap.get(sector);
    if (items && items.length > 0) {
      groups.push({ sector, items });
    }
  }
  // Add any remaining sectors not in SECTOR_ORDER
  for (const [sector, items] of sectorMap) {
    if (!SECTOR_ORDER.includes(sector) && items.length > 0) {
      groups.push({ sector, items });
    }
  }

  return (
    <div className="rounded-lg border bg-card overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30">
            <TableHead>Index Name</TableHead>
            <TableHead className="text-right">Last Price</TableHead>
            <TableHead className="text-right">Change %</TableHead>
            <TableHead className="text-right">Ratio</TableHead>
            <TableHead className="text-center">Signal</TableHead>
            <TableHead className="text-right">Ratio Ret ({period})</TableHead>
            <TableHead className="text-right">Index Ret ({period})</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {groups.map((group) => (
            <SectorSection
              key={group.sector}
              sector={group.sector}
              items={group.items}
              period={period}
            />
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

function SectorSection({
  sector,
  items,
  period,
}: {
  sector: string;
  items: LiveIndex[];
  period: string;
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
      {items.map((idx) => {
        const name = idx.nse_name || idx.index_name;
        const isTop25 = TOP_25_SET.has(name);
        const pctChange = idx.percentChange ?? null;
        const ratioReturn = idx.ratio_returns?.[period] ?? null;
        const indexReturn = idx.index_returns?.[period] ?? null;
        const signal = idx.signal as "BULLISH" | "BEARISH" | "NEUTRAL";

        return (
          <TableRow
            key={name}
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
                  : "text-red-600"
              )}
            >
              {pctChange != null ? formatPct(pctChange) : "---"}
            </TableCell>
            <TableCell className="text-right font-mono text-sm">
              {idx.ratio != null ? idx.ratio.toFixed(4) : "---"}
            </TableCell>
            <TableCell className="text-center">
              <SignalChip signal={signal} />
            </TableCell>
            <TableCell
              className={cn(
                "text-right font-mono text-sm",
                ratioReturn != null && ratioReturn >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
              )}
            >
              {ratioReturn != null ? formatPct(ratioReturn) : "---"}
            </TableCell>
            <TableCell
              className={cn(
                "text-right font-mono text-sm",
                indexReturn != null && indexReturn >= 0
                  ? "text-emerald-600"
                  : "text-red-600"
              )}
            >
              {indexReturn != null ? formatPct(indexReturn) : "---"}
            </TableCell>
          </TableRow>
        );
      })}
    </>
  );
}
