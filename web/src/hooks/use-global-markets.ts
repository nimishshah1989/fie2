"use client";
import useSWR from "swr";
import { fetchGlobalMarkets } from "@/lib/global-api";
import type { GlobalMarketsResponse } from "@/lib/global-types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useGlobalMarkets() {
  const { data, error, isLoading, mutate } = useSWR<GlobalMarketsResponse>(
    "global-markets",
    fetchGlobalMarkets,
    { refreshInterval: REFRESH_MARKET }
  );
  return {
    data: data ?? { success: false, markets: [], timestamp: "" },
    error,
    isLoading,
    mutate,
  };
}
