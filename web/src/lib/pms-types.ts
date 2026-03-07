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
  benchmark_nav: number | null;
}

export interface WinLossStats {
  total_scripts_traded: number;
  winning_trades: number;
  losing_trades: number;
  win_rate_pct: number;
  total_profit: number;
  total_loss: number;
  profit_factor: number | null;
  avg_win: number;
  avg_loss: number;
  best_trade: { script: string; pnl: number } | null;
  worst_trade: { script: string; pnl: number } | null;
  trades: { script: string; buy_amount: number; sell_amount: number; pnl: number; pnl_pct: number }[];
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
  benchmark_return_pct: number | null;
  benchmark_cagr_pct: number | null;
  benchmark_volatility_pct: number | null;
  benchmark_max_drawdown_pct: number | null;
  benchmark_sharpe_ratio: number | null;
  benchmark_sortino_ratio: number | null;
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

export interface RiskAnalytics {
  ulcer_index: number;
  positive_months: number;
  negative_months: number;
  total_months: number;
  hit_rate_monthly: number;
  best_month_pct: number;
  worst_month_pct: number;
  avg_positive_month_pct: number;
  avg_negative_month_pct: number;
  max_consecutive_loss_months: number;
  up_capture_ratio: number | null;
  down_capture_ratio: number | null;
  beta: number | null;
  correlation: number | null;
  information_ratio: number | null;
  benchmark_ulcer_index: number | null;
  benchmark_hit_rate: number | null;
  benchmark_best_month: number | null;
  benchmark_worst_month: number | null;
  benchmark_max_consecutive_loss: number | null;
  avg_cash_pct: number | null;
  max_cash_pct: number | null;
  current_cash_pct: number | null;
}
