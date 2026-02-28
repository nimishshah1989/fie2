// ============================================================================
// Jhaveri Intelligence Platform — Portfolio Types
// Model Portfolio Management module
// ============================================================================

export interface Portfolio {
  id: number;
  name: string;
  description: string | null;
  benchmark: string;
  status: "ACTIVE" | "ARCHIVED";
  created_at: string | null;
  updated_at: string | null;
  // Summary fields from list endpoint
  num_holdings: number;
  total_invested: number;
  current_value: number;
  realized_pnl: number;
  total_return_pct: number;
}

export interface PortfolioDetail {
  id: number;
  name: string;
  description: string | null;
  benchmark: string;
  status: "ACTIVE" | "ARCHIVED";
  created_at: string | null;
  updated_at: string | null;
}

export interface PortfolioHoldingRow {
  id: number;
  ticker: string;
  exchange: string;
  sector: string | null;
  quantity: number;
  avg_cost: number;
  total_cost: number;
  current_price: number | null;
  current_value: number | null;
  unrealized_pnl: number | null;
  unrealized_pnl_pct: number | null;
  day_change_pct: number | null;
  weight_pct: number | null;
  price_source: string | null;  // Yahoo Finance symbol used (e.g. LIQUIDBEES.NS)
}

export interface HoldingsTotals {
  total_invested: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
  num_holdings: number;
}

export interface PortfolioTransactionRow {
  id: number;
  ticker: string;
  exchange: string;
  txn_type: "BUY" | "SELL";
  quantity: number;
  price: number;
  total_value: number;
  txn_date: string;
  notes: string | null;
  realized_pnl: number | null;
  realized_pnl_pct: number | null;
  cost_basis_at_sell: number | null;
  created_at: string | null;
}

export interface NAVDataPoint {
  date: string;
  total_value: number;
  total_cost: number;
  unrealized_pnl: number;
  benchmark_value: number | null;
}

export interface PortfolioPerformance {
  total_invested: number;
  current_value: number;
  unrealized_pnl: number;
  unrealized_pnl_pct: number;
  realized_pnl: number;
  total_return: number;
  total_return_pct: number;
  xirr: number | null;
  cagr: number | null;
  max_drawdown: number | null;
  benchmark_return_pct: number | null;
  alpha: number | null;
}

export interface AllocationItem {
  label: string;
  value: number;
  pct: number;
}

export interface CreatePortfolioPayload {
  name: string;
  description?: string;
  benchmark?: string;
}

export interface CreateTransactionPayload {
  ticker: string;
  txn_type: "BUY" | "SELL";
  quantity: number;
  price: number;
  txn_date: string;
  notes?: string;
  exchange?: string;
  sector?: string;
}
