"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Calculator, LineChart, TrendingUp } from "lucide-react";

/** Portfolio Calculations + NAV Methodology + USDINR Returns */
export function DocsCalculations() {
  return (
    <>
      {/* ─── Portfolio Calculations ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Calculator className="h-4 w-4 text-primary" />
            Portfolio Calculations
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-5">
          <CalcSection title="Cost Basis (Weighted Average)">
            <p className="text-muted-foreground text-xs mb-2">
              When buying more of an existing holding, cost is averaged. Standard for Indian equity markets.
            </p>
            <Formula>
              new_avg_cost = (old_total_cost + new_buy_value) / new_total_qty{"\n"}
              total_cost = quantity &times; avg_cost
            </Formula>
          </CalcSection>

          <CalcSection title="Unrealized P&L">
            <Formula>
              unrealized_pnl = (CMP - avg_cost) &times; quantity{"\n"}
              unrealized_pnl_pct = ((CMP / avg_cost) - 1) &times; 100
            </Formula>
          </CalcSection>

          <CalcSection title="Realized P&L (on SELL)">
            <Formula>
              realized_pnl = (sell_price - avg_cost) &times; sell_qty{"\n"}
              realized_pnl_pct = ((sell_price / avg_cost) - 1) &times; 100
            </Formula>
          </CalcSection>

          <CalcSection title="Total Return">
            <Formula>
              total_return = (current_value - total_invested + realized_pnl) / total_invested &times; 100
            </Formula>
          </CalcSection>

          <CalcSection title="XIRR (Extended Internal Rate of Return)">
            <p className="text-muted-foreground text-xs mb-2">
              Annualized return accounting for timing of cash flows. Computed using Newton-Raphson method.
            </p>
            <Formula>
              Cash flows:{"\n"}
              {"  "}BUY transactions = negative (money out){"\n"}
              {"  "}SELL transactions = positive (money in){"\n"}
              {"  "}Current portfolio value = positive (on today&apos;s date){"\n"}
              {"\n"}
              Solve for r: &sum; CF_i / (1 + r)^((d_i - d_0) / 365) = 0
            </Formula>
          </CalcSection>

          <CalcSection title="CAGR (Compound Annual Growth Rate)">
            <Formula>
              end_value = current_value + cumulative_realized_pnl{"\n"}
              CAGR = ((end_value / start_cost) ^ (1 / years) - 1) &times; 100
            </Formula>
          </CalcSection>

          <CalcSection title="Max Drawdown">
            <p className="text-muted-foreground text-xs mb-2">
              Largest peak-to-trough decline in portfolio value from the NAV time series.
            </p>
            <Formula>
              For each point in NAV series:{"\n"}
              {"  "}running_max = max(running_max, nav_value){"\n"}
              {"  "}drawdown = (nav_value - running_max) / running_max &times; 100{"\n"}
              max_drawdown = min(all drawdowns)
            </Formula>
          </CalcSection>

          <CalcSection title="Alpha (vs Benchmark)">
            <Formula>
              alpha = portfolio_return_pct - benchmark_return_pct{"\n"}
              benchmark_return = (nifty_latest - nifty_at_first_nav) / nifty_at_first_nav &times; 100
            </Formula>
          </CalcSection>

          <CalcSection title="Portfolio Weight">
            <Formula>
              weight_pct = (holding_current_value / total_portfolio_value) &times; 100
            </Formula>
          </CalcSection>
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

          <CalcSection title="Daily NAV Computation">
            <Formula>
              For each holding in portfolio:{"\n"}
              {"  "}value = quantity &times; EOD_close_price (from IndexPrice table){"\n"}
              {"  "}If no price found, falls back to avg_cost{"\n"}
              {"\n"}
              total_value = sum of all holding values{"\n"}
              total_cost = sum of (quantity &times; avg_cost) for all holdings{"\n"}
              unrealized_pnl = total_value - total_cost{"\n"}
              realized_pnl_cumulative = sum of realized P&L from all SELL txns up to date
            </Formula>
          </CalcSection>

          <CalcSection title="Benchmark Normalization">
            <p className="text-muted-foreground text-xs mb-2">
              The NIFTY benchmark is normalized to make it comparable on the same chart as portfolio returns.
            </p>
            <Formula>
              benchmark_value = portfolio_cost_at_start &times; (nifty_today / nifty_at_start){"\n"}
              {"\n"}
              This shows: &quot;What if the same money was invested in NIFTY?&quot;
            </Formula>
          </CalcSection>

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

      {/* ─── USDINR Returns ─── */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <TrendingUp className="h-4 w-4 text-primary" />
            USDINR Returns
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm space-y-3">
          <p className="text-muted-foreground text-xs">
            Currency pair returns are inverted to reflect the Indian investor&apos;s perspective on
            rupee strength or weakness.
          </p>

          <CalcSection title="Inversion Logic">
            <Formula>
              USDINR rising (82 &rarr; 87): displayed as NEGATIVE (INR weakening){"\n"}
              USDINR falling (87 &rarr; 82): displayed as POSITIVE (INR strengthening)
            </Formula>
            <p className="text-muted-foreground text-xs mt-2">
              This inversion is applied to both absolute and ratio returns across all time periods.
              A rising USDINR rate means each dollar costs more rupees, which is unfavourable for
              Indian investors — hence shown in red.
            </p>
          </CalcSection>
        </CardContent>
      </Card>
    </>
  );
}

/* ─── Shared helpers ─── */

function CalcSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="font-semibold text-foreground mb-1">{title}</h4>
      {children}
    </div>
  );
}

function Formula({ children }: { children: React.ReactNode }) {
  return (
    <div className="bg-muted/50 rounded-lg p-3 font-mono text-xs whitespace-pre-line">
      {children}
    </div>
  );
}
