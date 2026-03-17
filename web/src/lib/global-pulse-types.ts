// Global Pulse — TypeScript Types
// 3-level drill-down: Global Index → Sector → Stock

export interface GlobalIndex {
  key: string;
  name: string;
  region: string;
  currency: string;
  last: number | null;
  ratio: number | null;
  signal: string;
  ratio_returns: Record<string, number | null>;
  index_returns: Record<string, number | null>;
  has_sectors: boolean;
  sector_count: number;
}

export interface GlobalIndicesResponse {
  success: boolean;
  count: number;
  base: string;
  base_name: string;
  regions: string[];
  indices: GlobalIndex[];
  timestamp: string;
  error?: string;
}

export interface GlobalSector {
  key: string;
  name: string;
  symbol: string;
  last: number | null;
  ratio_vs_parent: number | null;
  signal: string;
  ratio_returns_vs_parent: Record<string, number | null>;
  ratio_returns_vs_nifty: Record<string, number | null>;
  index_returns: Record<string, number | null>;
  has_stocks: boolean;
  stock_count: number;
}

export interface GlobalSectorsResponse {
  success: boolean;
  market: string;
  market_name: string;
  base: string;
  sectors: GlobalSector[];
  timestamp: string;
  message?: string;
  error?: string;
}

export interface GlobalStock {
  ticker: string;
  name: string;
  last: number | null;
  ratio_vs_sector: number | null;
  signal: string;
  ratio_returns: Record<string, number | null>;
  index_returns: Record<string, number | null>;
}

export interface GlobalStocksResponse {
  success: boolean;
  sector: string;
  sector_name: string;
  parent_index: string;
  parent_name: string;
  stocks: GlobalStock[];
  timestamp: string;
  message?: string;
  error?: string;
}
