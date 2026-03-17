/** Single global instrument (benchmark or sector ETF) */
export interface GlobalInstrument {
  key: string;
  name: string;
  close: number | null;
  date: string | null;
  change_pct: number | null;
  index_returns: Record<string, number | null>;
  relative_returns: Record<string, number | null>;
  sector?: string;
}

/** A single global market with its benchmark + sector ETFs */
export interface GlobalMarket {
  market_key: string;
  name: string;
  flag: string;
  benchmark: GlobalInstrument;
  sector_etfs: GlobalInstrument[];
}

/** Response from GET /api/global-markets/live */
export interface GlobalMarketsResponse {
  success: boolean;
  markets: GlobalMarket[];
  timestamp: string;
}
