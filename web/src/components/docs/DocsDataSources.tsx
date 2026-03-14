"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, Clock, Database } from "lucide-react";

export function DocsDataSources() {
  return (
    <>
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
                  <td className="px-4 py-2">EOD Stock &amp; Index Prices</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Yahoo Finance</Badge>
                    <span className="ml-1">via yfinance (Python)</span>
                  </td>
                  <td className="px-4 py-2">Daily at 3:30 PM IST</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Live Index Data (135+ indices)</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">nsetools</Badge>
                    <span className="ml-1">NSE India API wrapper</span>
                  </td>
                  <td className="px-4 py-2">Daily at 3:30 PM IST</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">Sector Index Constituents</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">NSE API</Badge>
                    <span className="ml-1">Sector constituents endpoint</span>
                  </td>
                  <td className="px-4 py-2">Daily (startup + EOD)</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2">TradingView Alerts</td>
                  <td className="px-4 py-2">
                    <Badge variant="outline" className="text-[10px]">Webhook</Badge>
                    <span className="ml-1">POST to /webhook/tradingview</span>
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
                  <td className="px-4 py-2 font-mono italic">All others</td>
                  <td className="px-4 py-2 font-mono italic">TICKER.NS</td>
                  <td className="px-4 py-2">NSE equity default</td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* ─── Automated Schedule ─── */}
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
                  <td className="px-4 py-2">Closing prices for all indices (135+), stocks, ETFs, and sector constituents</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">3:30 PM</td>
                  <td className="px-4 py-2">Sentiment Computation</td>
                  <td className="px-4 py-2">Market breadth metrics + per-stock sentiment scoring + sector aggregation</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">3:35 PM</td>
                  <td className="px-4 py-2">NAV Computation</td>
                  <td className="px-4 py-2">Daily NAV for all active portfolios using EOD prices</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">Real-time</td>
                  <td className="px-4 py-2">Webhook Processing</td>
                  <td className="px-4 py-2">TradingView alerts processed immediately on receipt</td>
                </tr>
                <tr className="border-t border-border">
                  <td className="px-4 py-2 font-mono">On-demand</td>
                  <td className="px-4 py-2">Live Price Fetch</td>
                  <td className="px-4 py-2">Holdings and alert pages fetch live CMP from Yahoo Finance on each load</td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="text-muted-foreground text-xs mt-3">
            Market pages auto-refresh every 5 minutes. Portfolio and basket pages refresh every 15 minutes.
          </p>
        </CardContent>
      </Card>
    </>
  );
}
