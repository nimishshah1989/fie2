"use client";
import useSWR from "swr";
import {
  fetchGlobalIndices,
  fetchGlobalSectors,
  fetchGlobalStocks,
} from "@/lib/global-pulse-api";
import type {
  GlobalIndicesResponse,
  GlobalSectorsResponse,
  GlobalStocksResponse,
} from "@/lib/global-pulse-types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useGlobalIndices(base: string) {
  return useSWR<GlobalIndicesResponse>(
    `global-indices-${base}`,
    () => fetchGlobalIndices(base),
    { refreshInterval: REFRESH_MARKET },
  );
}

export function useGlobalSectors(market: string | null, base: string) {
  return useSWR<GlobalSectorsResponse>(
    market ? `global-sectors-${market}-${base}` : null,
    () => fetchGlobalSectors(market!, base),
    { refreshInterval: REFRESH_MARKET },
  );
}

export function useGlobalStocks(sector: string | null) {
  return useSWR<GlobalStocksResponse>(
    sector ? `global-stocks-${sector}` : null,
    () => fetchGlobalStocks(sector!),
    { refreshInterval: REFRESH_MARKET },
  );
}
