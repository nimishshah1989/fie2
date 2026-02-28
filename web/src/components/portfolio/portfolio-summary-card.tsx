"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { formatPrice, formatPct } from "@/lib/utils";
import type { Portfolio } from "@/lib/portfolio-types";
import { Briefcase, TrendingUp, TrendingDown } from "lucide-react";

interface PortfolioSummaryCardProps {
  portfolio: Portfolio;
  onClick: () => void;
}

export function PortfolioSummaryCard({ portfolio, onClick }: PortfolioSummaryCardProps) {
  const isPositive = portfolio.total_return_pct >= 0;

  return (
    <Card
      className="cursor-pointer hover:shadow-md hover:border-primary/30 transition-all"
      onClick={onClick}
    >
      <CardContent className="p-4 space-y-3">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
              <Briefcase className="h-4 w-4 text-primary" />
            </div>
            <div>
              <h3 className="font-semibold text-sm text-foreground leading-tight">
                {portfolio.name}
              </h3>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wide">
                vs {portfolio.benchmark}
              </p>
            </div>
          </div>
          <Badge variant="outline" className="text-[10px]">
            {portfolio.num_holdings} holdings
          </Badge>
        </div>

        {/* Description */}
        {portfolio.description && (
          <p className="text-xs text-muted-foreground line-clamp-2">
            {portfolio.description}
          </p>
        )}

        {/* Metrics */}
        <div className="grid grid-cols-2 gap-3 pt-1">
          <div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Invested
            </div>
            <div className="text-sm font-semibold">
              {formatPrice(portfolio.total_invested)}
            </div>
          </div>
          <div>
            <div className="text-[10px] text-muted-foreground uppercase tracking-wide">
              Current
            </div>
            <div className="text-sm font-semibold">
              {formatPrice(portfolio.current_value)}
            </div>
          </div>
        </div>

        {/* Return */}
        <div className="flex items-center justify-between pt-1 border-t border-border">
          <span className="text-xs text-muted-foreground">Total Return</span>
          <div className={`flex items-center gap-1 text-sm font-bold ${
            isPositive ? "text-emerald-600" : "text-red-600"
          }`}>
            {isPositive ? (
              <TrendingUp className="h-3.5 w-3.5" />
            ) : (
              <TrendingDown className="h-3.5 w-3.5" />
            )}
            {formatPct(portfolio.total_return_pct)}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
