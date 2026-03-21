"use client";
import useSWR from "swr";
import {
  fetchCompassSectors,
  fetchCompassStocks,
  fetchCompassETFs,
  fetchModelPortfolio,
  fetchModelTrades,
  fetchModelNAV,
  fetchModelPerformance,
} from "@/lib/compass-api";
import type {
  SectorRS,
  StockRS,
  ETFRS,
  PortfolioState,
  ModelTrade,
  NAVPoint,
  PerformanceMetrics,
  Period,
} from "@/lib/compass-types";

// Refresh every 15 minutes — matches backend RS recomputation cycle
const REFRESH = 15 * 60_000; // 15 min

export function useCompassSectors(base: string, period: Period) {
  const { data, error, isLoading, mutate } = useSWR<SectorRS[]>(
    `compass-sectors-${base}-${period}`,
    () => fetchCompassSectors(base, period),
    { refreshInterval: REFRESH }
  );
  return { sectors: data ?? [], error, isLoading, mutate };
}

export function useCompassStocks(sectorKey: string | null, base: string, period: Period) {
  const { data, error, isLoading, mutate } = useSWR<StockRS[]>(
    sectorKey ? `compass-stocks-${sectorKey}-${base}-${period}` : null,
    () => (sectorKey ? fetchCompassStocks(sectorKey, base, period) : Promise.resolve([])),
    { refreshInterval: REFRESH }
  );
  return { stocks: data ?? [], error, isLoading, mutate };
}

export function useCompassETFs(base: string, period: Period) {
  const { data, error, isLoading, mutate } = useSWR<ETFRS[]>(
    `compass-etfs-${base}-${period}`,
    () => fetchCompassETFs(base, period),
    { refreshInterval: REFRESH }
  );
  return { etfs: data ?? [], error, isLoading, mutate };
}

export function useModelPortfolio() {
  const { data, error, isLoading, mutate } = useSWR<PortfolioState | null>(
    "compass-model-portfolio",
    fetchModelPortfolio,
    { refreshInterval: REFRESH }
  );
  return { portfolio: data, error, isLoading, mutate };
}

export function useModelTrades(limit = 50) {
  const { data, error, isLoading } = useSWR<ModelTrade[]>(
    `compass-model-trades-${limit}`,
    () => fetchModelTrades(limit),
    { refreshInterval: REFRESH }
  );
  return { trades: data ?? [], error, isLoading };
}

export function useModelNAV(days = 365) {
  const { data, error, isLoading } = useSWR<NAVPoint[]>(
    `compass-model-nav-${days}`,
    () => fetchModelNAV(days),
    { refreshInterval: REFRESH }
  );
  return { navHistory: data ?? [], error, isLoading };
}

export function useModelPerformance() {
  const { data, error, isLoading } = useSWR<PerformanceMetrics | null>(
    "compass-model-performance",
    fetchModelPerformance,
    { refreshInterval: REFRESH }
  );
  return { performance: data, error, isLoading };
}
