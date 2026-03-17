export interface MutualFund {
  code: string;
  name: string;
  category: string;
}

export interface MetricInfo {
  key: string;
  label: string;
  description?: string;
}

export interface Strategy {
  id: string;
  label: string;
  description: string;
  metric: string;
  threshold: number;
  multiplier: number;
}

export interface TimelinePoint {
  date: string;
  nav: number;
  regular_invested: number;
  regular_value: number;
  enhanced_invested: number;
  enhanced_value: number;
  is_trigger: boolean;
  in_cooloff: boolean;
  breadth_count: number | null;
}

export interface SimulationResult {
  success: boolean;
  fund_name: string;
  metric_label: string;
  reg_invested: number;
  reg_value: number;
  reg_units: number;
  reg_xirr: number | null;
  enh_invested: number;
  enh_value: number;
  enh_units: number;
  enh_xirr: number | null;
  alpha_value: number;
  alpha_pct: number;
  extra_invested: number;
  num_triggers: number;
  cooloff_skips: number;
  total_sips: number;
  timeline: TimelinePoint[];
  trigger_dates: string[];
}

export interface BatchRow {
  fund_code: string;
  fund_name: string;
  category: string;
  strategy_id: string;
  period_label: string;
  period_months: number | null;
  regular_invested: number;
  regular_value: number;
  regular_xirr: number | null;
  enhanced_invested: number;
  enhanced_value: number;
  enhanced_xirr: number | null;
  incremental_return_abs: number;
  incremental_return_pct: number;
  incremental_xirr: number | null;
  num_triggers: number;
  cooloff_skips: number;
  total_sips: number;
}

export interface BatchResponse {
  success: boolean;
  strategies: Strategy[];
  results: BatchRow[];
  errors: string[];
  funds_count: number;
  cached?: boolean;
  computed_at?: string | null;
  metrics?: MetricInfo[];
  thresholds?: number[];
}

export interface SimulationParams {
  fund_code: string;
  metric_key: string;
  stock_threshold: number;
  sip_amount: number;
  multiplier: number;
  start_date: string;
  duration_months: number | null;
  sip_day: number;
  cooloff_days: number;
}
