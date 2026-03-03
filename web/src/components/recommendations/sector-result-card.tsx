"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { cn, formatPrice } from "@/lib/utils";
import { SECTOR_COLORS } from "@/lib/constants";

interface TopStock {
  ticker: string;
  name: string;
  ratio_return_vs_sector: number | null;
  last_price: number | null;
  weight_pct: number | null;
  pe_ratio: number | null;
  eps: number | null;
  week_52_high: number | null;
  week_52_low: number | null;
  market_cap_cr: number | null;
}

interface RecommendedEtf {
  ticker: string;
  last_price: number | null;
}

export interface SectorResult {
  sector_key: string;
  sector_name: string;
  ratio_return: number | null;
  qualifies: boolean;
  top_stocks: TopStock[];
  recommended_etfs: RecommendedEtf[];
}

interface SectorResultCardProps {
  sector: SectorResult;
  threshold: number;
}

function formatMarketCap(crores: number | null): string {
  if (crores == null) return "---";
  if (crores >= 100000) return `${(crores / 100000).toFixed(1)}L Cr`;
  if (crores >= 1000) return `${(crores / 1000).toFixed(1)}K Cr`;
  return `${crores.toFixed(0)} Cr`;
}

function format52WRange(low: number | null, high: number | null): string {
  if (low == null && high == null) return "---";
  const lowStr = low != null ? `₹${formatPrice(low)}` : "?";
  const highStr = high != null ? `₹${formatPrice(high)}` : "?";
  return `${lowStr} — ${highStr}`;
}

export function SectorResultCard({ sector, threshold }: SectorResultCardProps) {
  const colors = SECTOR_COLORS[sector.sector_key];
  const borderColor = colors?.border || "border-gray-200";

  return (
    <Card className={cn("gap-0 border-l-4", borderColor)}>
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between flex-wrap gap-2">
          <div>
            <h4 className={cn("text-sm font-bold", colors?.text || "text-foreground")}>
              {sector.sector_name}
            </h4>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn(
                "text-xs font-mono font-semibold",
                sector.ratio_return != null && sector.ratio_return >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {sector.ratio_return != null
                  ? `${sector.ratio_return >= 0 ? "+" : ""}${sector.ratio_return.toFixed(2)}%`
                  : "---"}
              </span>
              <span className="text-[10px] text-muted-foreground">
                ratio return (threshold: {threshold.toFixed(1)}%)
              </span>
            </div>
          </div>
          {/* ETF Badges */}
          {sector.recommended_etfs.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {sector.recommended_etfs.map((etf) => (
                <Badge key={etf.ticker} variant="secondary" className="text-[10px] font-mono">
                  {etf.ticker}
                  {etf.last_price != null && (
                    <span className="ml-1 text-muted-foreground">
                      ₹{formatPrice(etf.last_price)}
                    </span>
                  )}
                </Badge>
              ))}
            </div>
          )}
        </div>

        {/* Stock Table */}
        {sector.top_stocks.length > 0 && (
          <div className="border rounded-lg overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="text-[10px] w-8">#</TableHead>
                  <TableHead className="text-[10px]">Ticker</TableHead>
                  <TableHead className="text-[10px]">Company</TableHead>
                  <TableHead className="text-[10px] text-right">vs Sector</TableHead>
                  <TableHead className="text-[10px] text-right">Price</TableHead>
                  <TableHead className="text-[10px] text-right">PE</TableHead>
                  <TableHead className="text-[10px] text-right">EPS</TableHead>
                  <TableHead className="text-[10px] text-right">52W Range</TableHead>
                  <TableHead className="text-[10px] text-right">Mkt Cap</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sector.top_stocks.map((stock, idx) => (
                  <TableRow key={stock.ticker}>
                    <TableCell className="text-xs text-muted-foreground">{idx + 1}</TableCell>
                    <TableCell className="font-mono text-xs font-medium">{stock.ticker}</TableCell>
                    <TableCell className="text-xs text-muted-foreground truncate max-w-[140px]">
                      {stock.name}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">
                      {stock.ratio_return_vs_sector != null ? (
                        <span className={cn(
                          stock.ratio_return_vs_sector >= 0 ? "text-emerald-600" : "text-red-600"
                        )}>
                          {stock.ratio_return_vs_sector >= 0 ? "+" : ""}
                          {stock.ratio_return_vs_sector.toFixed(2)}%
                        </span>
                      ) : (
                        <span className="text-muted-foreground">---</span>
                      )}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">
                      {stock.last_price != null ? `₹${formatPrice(stock.last_price)}` : "---"}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">
                      {stock.pe_ratio != null ? stock.pe_ratio.toFixed(1) : "---"}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono">
                      {stock.eps != null ? `₹${stock.eps.toFixed(1)}` : "---"}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono whitespace-nowrap">
                      {format52WRange(stock.week_52_low, stock.week_52_high)}
                    </TableCell>
                    <TableCell className="text-xs text-right font-mono whitespace-nowrap">
                      {stock.market_cap_cr != null ? `₹${formatMarketCap(stock.market_cap_cr)}` : "---"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        {sector.top_stocks.length === 0 && (
          <p className="text-xs text-muted-foreground py-2">
            No constituent data available. Trigger EOD fetch to populate index constituents.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
