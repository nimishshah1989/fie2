// ============================================================================
// Jhaveri Intelligence Platform — PMS Types
// Types for PMS NAV analytics, metrics, drawdowns, and transactions
// ============================================================================

export interface PmsNavRecord {
  date: string;
  nav: number;
  unit_nav: number | null;
  corpus: number | null;
  equity_holding: number | null;
  etf_investment: number | null;
  cash_equivalent: number | null;
  bank_balance: number | null;
  liquidity_pct: number | null;
  high_water_mark: number | null;
}

export interface PmsMetric {
  period: string;
  start_date: string | null;
  end_date: string | null;
  start_nav: number | null;
  end_nav: number | null;
  return_pct: number | null;
  cagr_pct: number | null;
  volatility_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
}

export interface DrawdownEvent {
  peak_date: string;
  peak_nav: number;
  trough_date: string | null;
  trough_nav: number | null;
  drawdown_pct: number | null;
  duration_days: number | null;
  recovery_date: string | null;
  recovery_days: number | null;
  status: "recovered" | "underwater";
}

export interface PmsTransactionRow {
  id: number;
  date: string;
  script: string;
  exchange: string;
  stno: string;
  buy_qty: number | null;
  buy_rate: number | null;
  buy_cost_rate: number | null;
  buy_amt_with_cost: number | null;
  sale_qty: number | null;
  sale_rate: number | null;
  sale_cost_rate: number | null;
  sale_amt_with_cost: number | null;
}

export interface MonthlyReturn {
  year: number;
  month: number;
  return_pct: number;
}

export interface PmsSummary {
  latest_date: string;
  latest_nav: number;
  latest_unit_nav: number | null;
  latest_corpus: number | null;
  latest_equity_holding: number | null;
  latest_etf_investment: number | null;
  latest_bank_balance: number | null;
  latest_liquidity_pct: number | null;
  latest_high_water_mark: number | null;
  first_date: string | null;
  first_nav: number | null;
  first_unit_nav: number | null;
  total_days: number;
  cagr_pct: number | null;
  max_drawdown_pct: number | null;
  sharpe_ratio: number | null;
  sortino_ratio: number | null;
  calmar_ratio: number | null;
  return_pct: number | null;
  volatility_pct: number | null;
}
