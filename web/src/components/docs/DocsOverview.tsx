"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Shield } from "lucide-react";

export function DocsOverview() {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Shield className="h-4 w-4 text-primary" />
          Platform Overview
        </CardTitle>
      </CardHeader>
      <CardContent className="text-sm text-muted-foreground space-y-3">
        <p>
          The Jhaveri Intelligence Platform is a fund manager&apos;s decision support system that combines
          technical analysis alerts from TradingView with model portfolio management, market sentiment
          analysis, and sector-level recommendations. It processes webhook signals, tracks FM actions,
          computes per-stock sentiment scores, and provides portfolio analytics — all from a unified dashboard.
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-2">
          <div className="rounded-lg border border-border p-3">
            <div className="text-xs font-semibold text-foreground mb-1">Alert System</div>
            <p className="text-xs">
              TradingView webhooks &rarr; FM review &rarr; approve/deny with trade params &rarr; track P&L.
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <div className="text-xs font-semibold text-foreground mb-1">Model Portfolios</div>
            <p className="text-xs">
              Create strategies, record buy/sell transactions, track NAV, benchmark against NIFTY, compute XIRR/CAGR.
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <div className="text-xs font-semibold text-foreground mb-1">Sentiment Engine</div>
            <p className="text-xs">
              22-metric per-stock scoring, sector-level aggregation, market breadth analysis, and daily zone tracking.
            </p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <div className="text-xs font-semibold text-foreground mb-1">Recommendations</div>
            <p className="text-xs">
              48 sector &amp; thematic indices analysed for relative outperformance against benchmark.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
