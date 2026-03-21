/** Sector Compass — TypeScript types */

export type Quadrant = "LEADING" | "WEAKENING" | "IMPROVING" | "LAGGING";
export type CompassAction =
  | "BUY"
  | "HOLD"
  | "WATCH_EMERGING"
  | "WATCH_RELATIVE"
  | "WATCH_EARLY"
  | "AVOID"
  | "SELL";
export type VolumeSignal = "ACCUMULATION" | "WEAK_RALLY" | "DISTRIBUTION" | "WEAK_DECLINE";
export type MarketRegime = "BULL" | "CAUTIOUS" | "CORRECTION" | "BEAR";
export type Period = "1M" | "3M" | "6M" | "12M";
export type PEZone = "VALUE" | "FAIR" | "STRETCHED" | "EXPENSIVE";

/** Check if an action is any WATCH variant */
export function isWatch(action: CompassAction): boolean {
  return action === "WATCH_EMERGING" || action === "WATCH_RELATIVE" || action === "WATCH_EARLY";
}

/** Human-readable action label */
export function actionLabel(action: CompassAction): string {
  switch (action) {
    case "BUY": return "BUY";
    case "HOLD": return "HOLD";
    case "WATCH_EMERGING": return "WATCH";
    case "WATCH_RELATIVE": return "WATCH";
    case "WATCH_EARLY": return "WATCH";
    case "AVOID": return "AVOID";
    case "SELL": return "SELL";
  }
}

/** Short WATCH sub-label for the variant */
export function watchSubLabel(action: CompassAction): string | null {
  switch (action) {
    case "WATCH_EMERGING": return "Emerging";
    case "WATCH_RELATIVE": return "Relative";
    case "WATCH_EARLY": return "Early";
    default: return null;
  }
}

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
  action_reason: string;
  pe_ratio: number | null;
  pe_zone: PEZone | null;
  etfs: string[];
  category: string;
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
  action_reason: string;
  pe_ratio: number | null;
  pe_zone: PEZone | null;
  weight_pct: number | null;
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
  action_reason: string;
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
