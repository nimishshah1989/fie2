export interface AlertAction {
  decision: "APPROVED" | "DENIED";
  action_call: string | null;
  is_ratio: boolean;
  ratio_long: string | null;
  ratio_short: string | null;
  ratio_numerator_ticker: string | null;
  ratio_denominator_ticker: string | null;
  priority: "IMMEDIATELY" | "WITHIN_A_WEEK" | "WITHIN_A_MONTH" | null;
  has_chart: boolean;
  chart_analysis: string[] | null;
  decision_at: string | null;
  fm_notes: string | null;
  entry_price_low: number | null;
  entry_price_high: number | null;
  stop_loss: number | null;
  target_price: number | null;
}

export interface Alert {
  id: number;
  ticker: string;
  exchange: string;
  interval: string;
  time_utc: string | null;
  timenow_utc: string | null;
  price_open: number | null;
  price_high: number | null;
  price_low: number | null;
  price_close: number | null;
  price_at_alert: number | null;
  volume: number | null;
  alert_data: string | null;
  alert_name: string;
  signal_direction: "BULLISH" | "BEARISH" | "NEUTRAL";
  status: "PENDING" | "APPROVED" | "DENIED";
  received_at: string | null;
  action: AlertAction | null;
}

export interface PerformanceAlert extends Alert {
  trigger_price: number | null;
  entry_price: number | null;
  current_price: number | null;
  return_pct: number | null;
  return_abs: number | null;
  days_since: number | null;
  is_ratio_trade: boolean;
  ratio_data: {
    numerator_ticker: string;
    denominator_ticker: string;
    numerator_price: number | null;
    denominator_price: number | null;
  } | null;
}

export interface ActionableAlert extends Alert {
  trigger_type: "SL_HIT" | "TP_HIT";
  entry_price: number;
  current_price: number;
  stop_loss: number | null;
  target_price: number | null;
  pnl_pct: number;
  pnl_abs: number;
  days_since: number | null;
  is_ratio_trade: boolean;
}

export interface LiveIndex {
  index_name: string;
  nse_name?: string;
  last: number | null;
  open?: number | null;
  high?: number | null;
  low?: number | null;
  previousClose?: number | null;
  variation?: number | null;
  percentChange?: number | null;
  ratio: number | null;
  signal: string;
  ratio_returns?: Record<string, number | null>;
  index_returns?: Record<string, number | null>;
}

export interface ActionRequest {
  alert_id: number;
  decision: "APPROVED" | "DENIED";
  action_call?: string;
  is_ratio?: boolean;
  ratio_long?: string;
  ratio_short?: string;
  ratio_numerator_ticker?: string;
  ratio_denominator_ticker?: string;
  priority?: string;
  chart_image_b64?: string;
  fm_notes?: string;
  entry_price_low?: number;
  entry_price_high?: number;
  stop_loss?: number;
  target_price?: number;
}

export interface StatusResponse {
  analysis_enabled: boolean;
  version: string;
}

export interface IndicesResponse {
  success: boolean;
  count: number;
  base: string;
  timestamp: string;
  indices: LiveIndex[];
  error?: string;
}
