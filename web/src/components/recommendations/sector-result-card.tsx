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

interface TopStock {
  ticker: string;
  name: string;
  ratio_return_vs_sector: number | null;
  last_price: number | null;
  weight_pct: number | null;
}

interface RecommendedEtf {
  ticker: string;
  last_price: number | null;
}

export interface QualifyingSector {
  sector_key: string;
  sector_name: string;
  ratio_return: number;
  threshold: number;
  top_stocks: TopStock[];
  recommended_etfs: RecommendedEtf[];
}

interface SectorResultCardProps {
  sector: QualifyingSector;
}

export function SectorResultCard({ sector }: SectorResultCardProps) {
  const excess = sector.ratio_return - sector.threshold;

  return (
    <Card className="gap-0">
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h4 className="text-sm font-bold text-foreground">{sector.sector_name}</h4>
            <div className="flex items-center gap-2 mt-1">
              <span className={cn(
                "text-xs font-mono font-semibold",
                sector.ratio_return >= 0 ? "text-emerald-600" : "text-red-600"
              )}>
                {sector.ratio_return >= 0 ? "+" : ""}{sector.ratio_return.toFixed(2)}% ratio
              </span>
              <span className="text-[10px] text-muted-foreground">
                (threshold: {sector.threshold.toFixed(1)}%, excess: +{excess.toFixed(2)}%)
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

        {/* Top Stocks Table */}
        {sector.top_stocks.length > 0 && (
          <div className="border rounded-lg overflow-hidden">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50">
                  <TableHead className="text-[10px]">#</TableHead>
                  <TableHead className="text-[10px]">Ticker</TableHead>
                  <TableHead className="text-[10px]">Company</TableHead>
                  <TableHead className="text-[10px] text-right">Ratio vs Sector</TableHead>
                  <TableHead className="text-[10px] text-right">Price</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sector.top_stocks.map((stock, idx) => (
                  <TableRow key={stock.ticker}>
                    <TableCell className="text-xs text-muted-foreground">{idx + 1}</TableCell>
                    <TableCell className="font-mono text-xs font-medium">{stock.ticker}</TableCell>
                    <TableCell className="text-xs text-muted-foreground truncate max-w-[160px]">
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
                      {stock.last_price != null ? `₹${formatPrice(stock.last_price)}` : "—"}
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
