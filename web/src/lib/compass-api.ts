/** Sector Compass — API client */

import type {
  SectorRS,
  StockRS,
  ETFRS,
  PortfolioState,
  ModelTrade,
  NAVPoint,
  PerformanceMetrics,
  Period,
  PortfolioType,
} from "./compass-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchCompassSectors(
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<SectorRS[]> {
  const res = await fetch(`${API}/api/compass/sectors?base=${base}&period=${period}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchCompassStocks(
  sectorKey: string,
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<StockRS[]> {
  const res = await fetch(
    `${API}/api/compass/sectors/${sectorKey}/stocks?base=${base}&period=${period}`
  );
  if (!res.ok) return [];
  return res.json();
}

export async function fetchCompassETFs(
  base: string = "NIFTY",
  period: Period = "3M"
): Promise<ETFRS[]> {
  const res = await fetch(`${API}/api/compass/etfs?base=${base}&period=${period}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelPortfolio(portfolioType: PortfolioType = "etf_only"): Promise<PortfolioState | null> {
  const res = await fetch(`${API}/api/compass/model-portfolio?portfolio_type=${portfolioType}`);
  if (!res.ok) return null;
  return res.json();
}

export async function fetchModelTrades(portfolioType: PortfolioType = "etf_only", limit = 50): Promise<ModelTrade[]> {
  const res = await fetch(`${API}/api/compass/model-portfolio/trades?portfolio_type=${portfolioType}&limit=${limit}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelNAV(portfolioType: PortfolioType = "etf_only", days = 365): Promise<NAVPoint[]> {
  const res = await fetch(`${API}/api/compass/model-portfolio/nav?portfolio_type=${portfolioType}&days=${days}`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchModelPerformance(portfolioType: PortfolioType = "etf_only"): Promise<PerformanceMetrics | null> {
  const res = await fetch(`${API}/api/compass/model-portfolio/performance?portfolio_type=${portfolioType}`);
  if (!res.ok) return null;
  return res.json();
}

export async function refreshCompass(): Promise<Record<string, unknown>> {
  const res = await fetch(`${API}/api/compass/refresh`, { method: "POST" });
  if (!res.ok) throw new Error("Refresh failed");
  return res.json();
}
