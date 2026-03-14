"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BarChart2,
  Compass,
  Layers,
  LayoutDashboard,
  TrendingUp,
} from "lucide-react";

/** Alert System + Actioned Cards + Sentiment + Recommendations + Microbaskets + Navigation */
export function DocsFeatures() {
  return (
    <>
      {/* ─── Alert System (2-page flow) ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Alert System (2-Page Flow)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            TradingView sends alerts via webhook. The platform uses a streamlined 2-page flow:
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">
              1. Command Center <code className="bg-muted px-1 rounded text-xs">/</code>
            </h4>
            <p className="text-muted-foreground text-xs mb-2">
              All incoming alerts (pending + actioned) shown in a unified view. Pending alerts have a
              &quot;Take Action&quot; button that opens the action modal — approve or deny with trade parameters
              (entry range, stop loss, target, chart analysis, FM notes) without leaving the page.
            </p>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">
              2. Actioned Cards <code className="bg-muted px-1 rounded text-xs">/actioned</code>
            </h4>
            <p className="text-muted-foreground text-xs mb-2">
              All FM-actioned alerts organized in 3 tabs:
            </p>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Active</strong> — open positions with unrealized P&L, days held, and live threshold status</li>
              <li><strong>Triggered</strong> — alerts where stop-loss or target price has been hit</li>
              <li><strong>Closed</strong> — manually closed trades with realized P&L</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Alert Fields</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Ticker</strong> — NSE symbol from TradingView</li>
              <li><strong>Timeframe</strong> — Chart interval (1D, 4H, 1H, etc.)</li>
              <li><strong>Signal Direction</strong> — BULLISH / BEARISH / NEUTRAL</li>
              <li><strong>Action Call</strong> — BUY / SELL / RATIO (for pair trades)</li>
              <li><strong>Entry Range, Stop Loss, Target</strong> — Risk management levels</li>
              <li><strong>Chart Analysis</strong> — AI-generated 8-point technical analysis</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* ─── Sentiment Engine ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <BarChart2 className="h-4 w-4 text-primary" />
            Sentiment Engine
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            The sentiment engine scores market health using 22 technical metrics across 5 weighted layers,
            computed daily after market close. Sentiment is tracked at three levels: market breadth
            (aggregate), sector-level, and per-stock.
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Scoring Layers</h4>
            <div className="bg-muted/50 rounded-lg p-3 text-xs space-y-1">
              <div className="flex justify-between"><span>Short-Term Momentum (above EMA 10/21, RSI)</span><span className="font-mono font-medium">20%</span></div>
              <div className="flex justify-between"><span>Broad Trend (above EMA 50/200, Golden Cross)</span><span className="font-mono font-medium">30%</span></div>
              <div className="flex justify-between"><span>Advance/Decline (advance ratio, volume ratio)</span><span className="font-mono font-medium">25%</span></div>
              <div className="flex justify-between"><span>Momentum (MACD bull cross, ROC positive)</span><span className="font-mono font-medium">15%</span></div>
              <div className="flex justify-between"><span>Extremes (52W high/low, above prev month high)</span><span className="font-mono font-medium">10%</span></div>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Zone Classification</h4>
            <div className="flex flex-wrap gap-2">
              <Badge className="bg-red-100 text-red-700 hover:bg-red-100 text-[10px]">Bear &lt;30</Badge>
              <Badge className="bg-amber-100 text-amber-700 hover:bg-amber-100 text-[10px]">Weak 30-44</Badge>
              <Badge className="bg-slate-100 text-slate-600 hover:bg-slate-100 text-[10px]">Neutral 45-54</Badge>
              <Badge className="bg-emerald-50 text-emerald-600 hover:bg-emerald-50 text-[10px]">Bullish 55-69</Badge>
              <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100 text-[10px]">Strong 70+</Badge>
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Three Views</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Market Breadth</strong> — aggregate composite gauge, 5-layer indicator rows, 20-week history chart</li>
              <li><strong>Sector Sentiment</strong> — grid of sector cards with avg score, zone, stock distribution, and top/bottom stocks</li>
              <li><strong>Per-Stock Detail</strong> — individual stock scores with metric breakdowns (EMA, RSI, MACD, 52W status)</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* ─── Recommendation Engine ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Compass className="h-4 w-4 text-primary" />
            Recommendation Engine
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            The recommendation engine analyses 48 NSE indices (26 sectoral + 22 thematic) against a benchmark
            (NIFTY 50 by default) to identify sectors with relative outperformance or underperformance.
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">How It Works</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              Periods: 1W, 1M, 3M, 6M, 12M<br/>
              Method: ratio = sector_return / benchmark_return<br/>
              Threshold: configurable (e.g., ratio &gt; 1.05 = outperforming)
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Coverage</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Sectoral</strong> — NIFTY Bank, IT, Pharma, Auto, Metal, Energy, FMCG, Realty, and 18 more</li>
              <li><strong>Thematic</strong> — Infrastructure, MNC, PSE, Commodities, EV, Defence, Capital Markets, and 15 more</li>
              <li><strong>Top stocks</strong> per sector shown with market cap, P/E ratio, and 52-week range</li>
              <li><strong>ETF mapping</strong> for 7 sectors — BANKBEES, ITBEES, CPSE, JUNIORBEES, GOLDBEES, NIFTYBEES, METALIETF</li>
            </ul>
          </div>
        </CardContent>
      </Card>

      {/* ─── Microbaskets ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Layers className="h-4 w-4 text-primary" />
            Microbaskets
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            Microbaskets are curated stock baskets with weighted constituents. Each basket card shows
            status (Active/Stopped/Paused/Archived), portfolio size, current worth, P&L, and constituent breakdown.
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">CSV Upload Format</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              basket_name, ticker, company_name, weight(%), price, quantity
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Unit Computation</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              When portfolio_size is set:<br/>
              &nbsp;&nbsp;units = weight% &times; portfolio_size / price<br/>
              <br/>
              NAV is computed in background from constituent EOD prices.
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Basket as Portfolio Instrument</h4>
            <p className="text-muted-foreground text-xs">
              Baskets can be added to portfolios using the <code className="bg-muted px-1 rounded">MB_</code> prefix
              (e.g., <code className="bg-muted px-1 rounded">MB_MOMENTUM</code>) with instrument
              type <Badge variant="outline" className="text-[10px]">BASKET</Badge>.
              The basket&apos;s NAV is used as the instrument price in the portfolio.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ─── Navigation ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <LayoutDashboard className="h-4 w-4 text-primary" />
            Navigation (8 Pages)
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium text-foreground">Page</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Path</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Purpose</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground text-xs">
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Command Center</td>
                  <td className="px-4 py-2 font-mono">/</td>
                  <td className="px-4 py-2">All alerts with inline Take Action modal for pending items</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Actioned Cards</td>
                  <td className="px-4 py-2 font-mono">/actioned</td>
                  <td className="px-4 py-2">FM-actioned alerts: Active / Triggered / Closed tabs with P&L</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Market Pulse</td>
                  <td className="px-4 py-2 font-mono">/pulse</td>
                  <td className="px-4 py-2">Live market indices with period returns (1D to 12M)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Sentiment</td>
                  <td className="px-4 py-2 font-mono">/sentiment</td>
                  <td className="px-4 py-2">Market breadth gauge + sector sentiment grid + per-stock detail</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Recommendations</td>
                  <td className="px-4 py-2 font-mono">/recommendations</td>
                  <td className="px-4 py-2">48 sector/thematic indices vs benchmark analysis</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Model Portfolios</td>
                  <td className="px-4 py-2 font-mono">/portfolios</td>
                  <td className="px-4 py-2">Portfolio CRUD, holdings, NAV chart, XIRR/CAGR tracking</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Microbaskets</td>
                  <td className="px-4 py-2 font-mono">/microbaskets</td>
                  <td className="px-4 py-2">Curated stock baskets with rich cards showing status, P&L, constituents</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-medium text-foreground">Documentation</td>
                  <td className="px-4 py-2 font-mono">/docs</td>
                  <td className="px-4 py-2">This page — platform reference and calculation methodology</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Badge Counts</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Command Center</strong> — red badge showing the count of pending (unreviewed) alerts</li>
              <li><strong>Actioned Cards</strong> — red badge showing the count of triggered (SL/TP hit) alerts</li>
            </ul>
          </div>
        </CardContent>
      </Card>
    </>
  );
}
