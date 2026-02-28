"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  BookOpen,
  Calculator,
  Database,
  LineChart,
  TrendingUp,
  Briefcase,
  Activity,
  Clock,
  Shield,
} from "lucide-react";

export default function DocsPage() {
  return (
    <div className="space-y-8 max-w-4xl">
      {/* Page Header */}
      <div>
        <div className="flex items-center gap-2">
          <BookOpen className="size-6 text-primary" />
          <h1 className="text-2xl font-bold text-foreground">Documentation</h1>
        </div>
        <p className="text-sm text-muted-foreground mt-1">
          Complete reference for the Jhaveri Intelligence Platform — formulas, data sources, and methodology
        </p>
      </div>

      {/* ─── Platform Overview ─── */}
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
            technical analysis alerts from TradingView with model portfolio management. It processes
            webhook signals, tracks FM actions, and provides portfolio analytics — all from a single dashboard.
          </p>
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="rounded-lg border border-border p-3">
              <div className="text-xs font-semibold text-foreground mb-1">Alert System</div>
              <p className="text-xs">Receives TradingView webhooks, presents to FM for action, tracks performance of approved/denied signals.</p>
            </div>
            <div className="rounded-lg border border-border p-3">
              <div className="text-xs font-semibold text-foreground mb-1">Model Portfolios</div>
              <p className="text-xs">Create strategies, record buy/sell transactions, track NAV, benchmark against NIFTY, compute XIRR/CAGR.</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ─── Data Sources ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Database className="h-4 w-4 text-primary" />
            Data Sources
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-4">
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium text-foreground">Data Type</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Source</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Frequency</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Live Stock Prices (CMP)</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Yahoo Finance API</Badge>
                    <span className="ml-1">v8 chart endpoint</span>
                  </td>
                  <td className="px-4 py-2">Real-time (on page load)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">EOD Stock Prices</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Yahoo Finance</Badge>
                    <span className="ml-1">via yfinance (Python)</span>
                  </td>
                  <td className="px-4 py-2">Daily at 3:30 PM IST</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Index Data (NIFTY, BANKNIFTY)</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Yahoo Finance</Badge>
                    <span className="ml-1">^NSEI, ^NSEBANK symbols</span>
                  </td>
                  <td className="px-4 py-2">Daily at 3:30 PM IST</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">TradingView Alerts</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Webhook</Badge>
                    <span className="ml-1">TradingView POST to /webhook/tradingview</span>
                  </td>
                  <td className="px-4 py-2">Real-time</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Portfolio Transactions</td>
                  <td className="px-4 py-2">Manual entry by Fund Manager</td>
                  <td className="px-4 py-2">On-demand</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 text-xs text-amber-800">
            <strong>LIQUIDCASE</strong> maps to <code className="bg-amber-100 px-1 rounded">LIQUIDBEES.NS</code> on Yahoo Finance.
            This is the Nippon India ETF Liquid BeES — India&apos;s most liquid overnight fund ETF.
            CMP displayed is the real-time market price from Yahoo, not a synthetic value.
          </div>
        </CardContent>
      </Card>

      {/* ─── Ticker Mappings ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Activity className="h-4 w-4 text-primary" />
            Ticker to Yahoo Finance Symbol Mappings
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-muted-foreground text-xs mb-3">
            Portfolio tickers are mapped to Yahoo Finance symbols for price fetching. Default mapping: <code className="bg-muted px-1 rounded">TICKER</code> &rarr; <code className="bg-muted px-1 rounded">TICKER.NS</code> (NSE).
            Special mappings below:
          </p>
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium text-foreground">Portfolio Ticker</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Yahoo Symbol</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Description</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">LIQUIDCASE</td>
                  <td className="px-4 py-2 font-mono">LIQUIDBEES.NS</td>
                  <td className="px-4 py-2">Nippon India ETF Liquid BeES (overnight fund)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">CPSEETF</td>
                  <td className="px-4 py-2 font-mono">CPSEETF.NS</td>
                  <td className="px-4 py-2">CPSE ETF</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">METALETF</td>
                  <td className="px-4 py-2 font-mono">METALIETF.NS</td>
                  <td className="px-4 py-2">ICICI Prudential Metal ETF</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">SENSEXETF</td>
                  <td className="px-4 py-2 font-mono">SENSEXETF.NS</td>
                  <td className="px-4 py-2">Sensex ETF</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono italic">All others</td>
                  <td className="px-4 py-2 font-mono italic">TICKER.NS</td>
                  <td className="px-4 py-2">NSE equity default</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ─── Portfolio Calculations ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Calculator className="h-4 w-4 text-primary" />
            Portfolio Calculations
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-5">
          {/* Cost Basis */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Cost Basis (Weighted Average)</h4>
            <p className="text-muted-foreground text-xs mb-2">
              When buying more of an existing holding, cost is averaged. Standard for Indian equity markets.
            </p>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              new_avg_cost = (old_total_cost + new_buy_value) / new_total_qty<br/>
              total_cost = quantity &times; avg_cost
            </div>
          </div>

          {/* Unrealized P&L */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Unrealized P&L</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              unrealized_pnl = (CMP - avg_cost) &times; quantity<br/>
              unrealized_pnl_pct = ((CMP / avg_cost) - 1) &times; 100
            </div>
          </div>

          {/* Realized P&L */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Realized P&L (on SELL)</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              realized_pnl = (sell_price - avg_cost) &times; sell_qty<br/>
              realized_pnl_pct = ((sell_price / avg_cost) - 1) &times; 100
            </div>
          </div>

          {/* Total Return */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Total Return</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              total_return = (current_value - total_invested + realized_pnl) / total_invested &times; 100
            </div>
          </div>

          {/* XIRR */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">XIRR (Extended Internal Rate of Return)</h4>
            <p className="text-muted-foreground text-xs mb-2">
              Annualized return accounting for timing of cash flows. Computed using Newton-Raphson method.
            </p>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              Cash flows:<br/>
              &nbsp;&nbsp;BUY transactions = negative (money out)<br/>
              &nbsp;&nbsp;SELL transactions = positive (money in)<br/>
              &nbsp;&nbsp;Current portfolio value = positive (on today&apos;s date)<br/>
              <br/>
              Solve for r: &sum; CF_i / (1 + r)^((d_i - d_0) / 365) = 0
            </div>
          </div>

          {/* CAGR */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">CAGR (Compound Annual Growth Rate)</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              end_value = current_value + cumulative_realized_pnl<br/>
              CAGR = ((end_value / start_cost) ^ (1 / years) - 1) &times; 100
            </div>
          </div>

          {/* Max Drawdown */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Max Drawdown</h4>
            <p className="text-muted-foreground text-xs mb-2">
              Largest peak-to-trough decline in portfolio value from the NAV time series.
            </p>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              For each point in NAV series:<br/>
              &nbsp;&nbsp;running_max = max(running_max, nav_value)<br/>
              &nbsp;&nbsp;drawdown = (nav_value - running_max) / running_max &times; 100<br/>
              max_drawdown = min(all drawdowns)
            </div>
          </div>

          {/* Alpha */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Alpha (vs Benchmark)</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              alpha = portfolio_return_pct - benchmark_return_pct<br/>
              <br/>
              benchmark_return = (nifty_latest - nifty_at_first_nav) / nifty_at_first_nav &times; 100
            </div>
          </div>

          {/* Weight */}
          <div>
            <h4 className="font-semibold text-foreground mb-1">Portfolio Weight</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              weight_pct = (holding_current_value / total_portfolio_value) &times; 100
            </div>
          </div>
        </CardContent>
      </Card>

      {/* ─── NAV Computation ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <LineChart className="h-4 w-4 text-primary" />
            NAV (Net Asset Value) Methodology
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            NAV is computed daily for each portfolio using end-of-day closing prices. The NAV time series
            powers the performance chart.
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Daily NAV Computation</h4>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              For each holding in portfolio:<br/>
              &nbsp;&nbsp;value = quantity &times; EOD_close_price (from IndexPrice table)<br/>
              &nbsp;&nbsp;If no price found, falls back to avg_cost<br/>
              <br/>
              total_value = sum of all holding values<br/>
              total_cost = sum of (quantity &times; avg_cost) for all holdings<br/>
              unrealized_pnl = total_value - total_cost<br/>
              realized_pnl_cumulative = sum of realized P&L from all SELL transactions up to date
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Benchmark Normalization</h4>
            <p className="text-muted-foreground text-xs mb-2">
              The NIFTY benchmark is normalized to make it comparable on the same chart as portfolio returns.
            </p>
            <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs">
              benchmark_value = portfolio_cost_at_start &times; (nifty_today / nifty_at_start)<br/>
              <br/>
              This shows: &quot;What if the same money was invested in NIFTY?&quot;
            </div>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Chart Mode: Percentage Returns</h4>
            <p className="text-muted-foreground text-xs">
              The performance chart displays percentage returns from the first data point (period start).
              All three lines — Portfolio, Cost Basis, and NIFTY — start at 0% for easy comparison.
              Hover shows both % return and absolute values.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ─── Schedule ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Clock className="h-4 w-4 text-primary" />
            Automated Schedule
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium text-foreground">Time (IST)</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Task</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Description</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">3:30 PM</td>
                  <td className="px-4 py-2">EOD Price Fetch</td>
                  <td className="px-4 py-2">Fetches closing prices for all tracked indices and stocks</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">3:35 PM</td>
                  <td className="px-4 py-2">NAV Computation</td>
                  <td className="px-4 py-2">Computes daily NAV for all active portfolios using EOD prices</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">Real-time</td>
                  <td className="px-4 py-2">Webhook Processing</td>
                  <td className="px-4 py-2">TradingView alerts processed immediately on receipt</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">On-demand</td>
                  <td className="px-4 py-2">Live Price Fetch</td>
                  <td className="px-4 py-2">Holdings page fetches live CMP from Yahoo Finance on each load</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ─── Alert System ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            Alert System
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            TradingView sends alerts via webhook. The FM reviews each alert and takes action (Approve/Deny).
            Approved alerts can have trade parameters, chart analysis, and FM notes attached.
          </p>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Alert Fields</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Ticker</strong> — NSE symbol from TradingView</li>
              <li><strong>Timeframe</strong> — Chart interval (1D, 4H, 1H, etc.)</li>
              <li><strong>Signal Direction</strong> — BULLISH / BEARISH / NEUTRAL</li>
              <li><strong>OHLCV</strong> — Open, High, Low, Close, Volume at alert time</li>
              <li><strong>Alert Data</strong> — Custom message from TradingView strategy</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">FM Action Fields</h4>
            <ul className="text-muted-foreground text-xs space-y-1 list-disc list-inside">
              <li><strong>Action Call</strong> — BUY / SELL / RATIO (for pair trades)</li>
              <li><strong>Priority</strong> — IMMEDIATELY / WITHIN A WEEK / WITHIN A MONTH</li>
              <li><strong>Entry Range</strong> — Low and high entry price targets</li>
              <li><strong>Stop Loss & Target</strong> — Risk management levels</li>
              <li><strong>Chart Analysis</strong> — AI-generated 8-point technical analysis</li>
              <li><strong>FM Notes</strong> — Free-form fund manager commentary</li>
            </ul>
          </div>

          <div>
            <h4 className="font-semibold text-foreground mb-1">Alert Performance Tracking</h4>
            <p className="text-muted-foreground text-xs">
              After approval, the platform tracks price movement from the alert price to current market price,
              calculating P&L for each approved signal. This helps evaluate signal quality over time.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* ─── Architecture ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Briefcase className="h-4 w-4 text-primary" />
            Technical Architecture
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <div className="overflow-hidden rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-muted/50">
                  <th className="text-left px-4 py-2 font-medium text-foreground">Layer</th>
                  <th className="text-left px-4 py-2 font-medium text-foreground">Technology</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Frontend</td>
                  <td className="px-4 py-2">Next.js 14 + TypeScript + Tailwind CSS + shadcn/ui</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Backend API</td>
                  <td className="px-4 py-2">Python FastAPI (single server on port 8000)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Database</td>
                  <td className="px-4 py-2">PostgreSQL (Railway) / SQLite (local dev)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">ORM</td>
                  <td className="px-4 py-2">SQLAlchemy</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Charts</td>
                  <td className="px-4 py-2">Recharts (area, line, pie)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Scheduling</td>
                  <td className="px-4 py-2">APScheduler (CronTrigger for daily tasks)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Deployment</td>
                  <td className="px-4 py-2">Railway (auto-deploy from git push)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Market Data</td>
                  <td className="px-4 py-2">Yahoo Finance (yfinance + curl fallback)</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Footer */}
      <div className="text-xs text-muted-foreground pb-8">
        <p>Jhaveri Intelligence Platform v3 &mdash; Built for Jhaveri Securities & Ventures</p>
      </div>
    </div>
  );
}
