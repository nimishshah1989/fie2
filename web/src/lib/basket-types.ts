// ============================================================================
// Jhaveri Intelligence Platform — Microbasket Types
// Custom stock baskets with ratio analysis & portfolio integration
// ============================================================================

export interface BasketConstituent {
  ticker: string;
  company_name: string | null;
  weight_pct: number;
  current_price?: number | null;
  weighted_value?: number | null;
  computed_units?: number | null;
  allocated_amount?: number | null;
}

export interface BasketSummary {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  benchmark: string;
  portfolio_size?: number | null;
  num_constituents: number;
  current_value: number | null;
  value_date: string | null;
  created_at: string | null;
}

export interface BasketLiveItem {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  benchmark: string;
  portfolio_size?: number | null;
  num_constituents: number;
  current_value: number | null;
  value_date: string | null;
  change_pct: number | null;
  ratio_returns: Record<string, number | null>;
  index_returns: Record<string, number | null>;
  constituents: BasketConstituent[];
}

export interface BasketLiveResponse {
  success: boolean;
  count: number;
  base: string;
  baskets: BasketLiveItem[];
  timestamp: string;
}

export interface BasketDetail {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  benchmark: string;
  portfolio_size?: number | null;
  status: "ACTIVE" | "ARCHIVED";
  current_value: number | null;
  num_constituents: number;
  constituents: BasketConstituent[];
  created_at: string | null;
  updated_at: string | null;
}

export interface ConstituentInput {
  ticker: string;
  company_name?: string;
  weight_pct: number;
}

export interface CreateBasketPayload {
  name: string;
  description?: string;
  benchmark?: string;
  portfolio_size?: number;
  constituents: ConstituentInput[];
}

export interface UpdateBasketPayload {
  name?: string;
  description?: string;
  benchmark?: string;
  portfolio_size?: number;
  constituents?: ConstituentInput[];
}

export interface CsvUploadResult {
  basket_name: string;
  success: boolean;
  id?: number;
  slug?: string;
  num_constituents?: number;
  error?: string;
}

export interface CsvUploadResponse {
  success: boolean;
  rows_parsed: number;
  baskets_found: number;
  results: CsvUploadResult[];
}
