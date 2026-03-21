/** Sector Compass — TypeScript types */

export type Quadrant = "LEADING" | "WEAKENING" | "IMPROVING" | "LAGGING";
export type CompassAction = "BUY" | "HOLD" | "WATCH" | "SELL";
export type VolumeSignal = "ACCUMULATION" | "WEAK_RALLY" | "DISTRIBUTION" | "WEAK_DECLINE";
export type MarketRegime = "BULL" | "CAUTIOUS" | "CORRECTION" | "BEAR";
export type Period = "1M" | "3M" | "6M" | "12M";

export interface SectorRS {
  sector_key: string;
  display_name: string;
  rs_score: number;
  rs_momentum: number;
  relative_return: number;
  absolute_return: number | null;
  volume_signal: VolumeSignal | null;
  quadrant: Quadrant;
  action: CompassAction;
  conviction: number;
  etfs: string[];
  category: string;
  pe_ratio: number | null;
  market_regime: MarketRegime | null;
  last_updated: string | null;
}

export interface StockRS {
  ticker: string;
  company_name: string;
  rs_score: number;
  rs_momentum: number;
  relative_return: number;
  absolute_return: number | null;
  volume_signal: VolumeSignal | null;
  quadrant: Quadrant;
  action: CompassAction;
  conviction: number;
  weight_pct: number | null;
  stop_loss_pct: number | null;
  pe_ratio: number | null;
}

export interface ETFRS {
  ticker: string;
  parent_sector: string | null;
  sector_name: string | null;
  rs_score: number;
  rs_momentum: number;
  relative_return: number;
  absolute_return: number | null;
  volume_signal: VolumeSignal | null;
  quadrant: Quadrant;
  action: CompassAction;
  conviction: number;
}

export type PortfolioType = "etf_only" | "stock_etf" | "stock_only";

export interface PortfolioPosition {
  sector_key: string;
  sector_name: string;
  instrument_id: string;
  instrument_type: string;
  entry_date: string;
  entry_price: number;
  current_price: number | null;
  weight_pct: number | null;
  volatility: number | null;
  stop_loss: number | null;
  trailing_stop: number | null;
  pnl_pct: number | null;
  holding_days: number | null;
  tax_type: string | null;
  status: string;
}

export interface ModelTrade {
  trade_date: string;
  sector_key: string;
  sector_name: string;
  instrument_id: string;
  instrument_type: string;
  side: string;
  price: number;
  value: number | null;
  reason: string | null;
  quadrant: Quadrant | null;
  rs_score: number | null;
  pnl_pct: number | null;
  tax_impact: number | null;
}

export interface NAVPoint {
  date: string;
  nav: number;
  benchmark_nav: number | null;
  fm_nav: number | null;
  cash_pct: number | null;
  num_positions: number | null;
  max_drawdown: number | null;
}

export interface PortfolioState {
  portfolio_type: PortfolioType;
  positions: PortfolioPosition[];
  num_open: number;
  max_positions: number;
  nav: NAVPoint | null;
  initial_capital: number;
}

export interface PerformanceMetrics {
  portfolio_type: PortfolioType;
  total_return_pct: number;
  benchmark_return_pct: number;
  alpha_vs_nifty: number;
  alpha_vs_fm: number | null;
  max_drawdown_pct: number;
  win_rate_pct: number;
  total_trades: number;
  avg_holding_days: number;
  total_tax_paid: number;
  start_date: string;
  end_date: string;
  current_nav: number;
}
