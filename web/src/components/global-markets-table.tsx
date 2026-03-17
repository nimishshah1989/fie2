"use client";

import { useState } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn } from "@/lib/utils";
import type { GlobalMarket, GlobalInstrument } from "@/lib/global-types";

function fmtPrice(v: number | null): string {
  if (v == null) return "—";
  if (v > 1000) return v.toLocaleString("en-US", { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  return v.toFixed(2);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || v === undefined) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}

function pctColor(v: number | null | undefined): string {
  if (v == null || v === undefined) return "";
  return v >= 0 ? "text-emerald-600" : "text-red-600";
}

const PERIOD_TABS = ["1d", "1w", "1m", "3m", "6m", "12m"] as const;

interface GlobalMarketsTableProps {
  markets: GlobalMarket[];
  timestamp?: string;
}

export function GlobalMarketsTable({ markets }: GlobalMarketsTableProps) {
  const [period, setPeriod] = useState<string>("1m");

  return (
    <div className="space-y-4">
      {/* Period selector */}
      <div className="flex items-center gap-1">
        {PERIOD_TABS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => setPeriod(p)}
            className={cn(
              "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
              period === p
                ? "bg-teal-600 text-white"
                : "bg-slate-100 text-slate-600 hover:bg-slate-200"
            )}
          >
            {p.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Market cards */}
      {markets.map((market) => (
        <MarketCard key={market.market_key} market={market} period={period} />
      ))}
    </div>
  );
}

function MarketCard({ market, period }: { market: GlobalMarket; period: string }) {
  const bm = market.benchmark;
  const hasSectorETFs = market.sector_etfs.length > 0;

  return (
    <div className="rounded-xl border border-slate-200 bg-white overflow-hidden">
      {/* Market header with benchmark */}
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50/80 border-b border-slate-100">
        <div className="flex items-center gap-2">
          <span className="text-lg">{market.flag}</span>
          <div>
            <h3 className="text-sm font-semibold text-slate-800">{market.name}</h3>
            <span className="text-xs text-slate-500">{bm.name}</span>
          </div>
        </div>
        <div className="text-right">
          <p className="text-base font-bold font-mono text-slate-800">{fmtPrice(bm.close)}</p>
          <p className={cn("text-xs font-mono", pctColor(bm.change_pct))}>
            {fmtPct(bm.change_pct)}
          </p>
        </div>
      </div>

      {/* Benchmark period returns */}
      <div className="px-4 py-2 border-b border-slate-100">
        <div className="flex items-center gap-4 text-xs">
          <span className="text-slate-400 font-medium w-20">Benchmark</span>
          {PERIOD_TABS.map((p) => {
            const val = bm.index_returns[p] ?? null;
            return (
              <div key={p} className="text-center min-w-[52px]">
                <span className="text-[10px] text-slate-400 uppercase block">{p}</span>
                <span className={cn("font-mono text-xs", p === period ? "font-bold" : "", pctColor(val))}>
                  {fmtPct(val)}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Sector ETFs table */}
      {hasSectorETFs && (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="bg-muted/20">
                <TableHead className="text-xs">Sector ETF</TableHead>
                <TableHead className="text-right text-xs">Price</TableHead>
                <TableHead className="text-right text-xs">Change</TableHead>
                <TableHead className="text-right text-xs">
                  Return ({period.toUpperCase()})
                </TableHead>
                <TableHead className="text-right text-xs">
                  vs {bm.name}
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {market.sector_etfs.map((etf) => (
                <SectorETFRow key={etf.key} etf={etf} period={period} benchmarkName={bm.name} />
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      {!hasSectorETFs && (
        <div className="px-4 py-3 text-xs text-slate-400 text-center">
          Index only — no sector ETF breakdown available
        </div>
      )}
    </div>
  );
}

function SectorETFRow({
  etf,
  period,
}: {
  etf: GlobalInstrument;
  period: string;
  benchmarkName: string;
}) {
  const indexRet = etf.index_returns[period] ?? null;
  const relRet = etf.relative_returns[period] ?? null;

  return (
    <TableRow>
      <TableCell className="text-sm font-medium">{etf.sector || etf.name}</TableCell>
      <TableCell className="text-right font-mono text-sm">{fmtPrice(etf.close)}</TableCell>
      <TableCell className={cn("text-right font-mono text-sm", pctColor(etf.change_pct))}>
        {fmtPct(etf.change_pct)}
      </TableCell>
      <TableCell className={cn("text-right font-mono text-sm", pctColor(indexRet))}>
        {fmtPct(indexRet)}
      </TableCell>
      <TableCell className="text-right">
        <RelativeBadge value={relRet} />
      </TableCell>
    </TableRow>
  );
}

function RelativeBadge({ value }: { value: number | null | undefined }) {
  if (value == null || value === undefined) return <span className="text-xs text-slate-400">—</span>;

  const isPositive = value >= 0;
  return (
    <span
      className={cn(
        "inline-flex items-center text-xs font-mono font-medium rounded-full px-2 py-0.5 border",
        isPositive
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-red-50 text-red-700 border-red-200"
      )}
    >
      {isPositive ? "▲" : "▼"} {fmtPct(value)}
    </span>
  );
}
