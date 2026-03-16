export interface MutualFund {
  code: string;
  name: string;
  category: string;
}

export interface BreadthMetric {
  key: string;
  label: string;
  layer: "short_term" | "broad_trend";
}

export interface TimelinePoint {
  date: string;
  nav: number;
  regular_invested: number;
  regular_value: number;
  enhanced_invested: number;
  enhanced_value: number;
  is_trigger: boolean;
  breadth_count: number | null;
  breadth_total: number | null;
}

export interface SimulationResult {
  fund_name: string;
  metric_label: string;
  regular_total_invested: number;
  regular_current_value: number;
  regular_units: number;
  regular_xirr: number | null;
  enhanced_total_invested: number;
  enhanced_current_value: number;
  enhanced_units: number;
  enhanced_xirr: number | null;
  alpha_value: number;
  alpha_pct: number;
  extra_invested: number;
  num_triggers: number;
  total_sip_count: number;
  timeline: TimelinePoint[];
  trigger_dates: string[];
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
}
