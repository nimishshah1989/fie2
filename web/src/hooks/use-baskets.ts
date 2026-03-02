"use client";

import useSWR from "swr";
import { fetchBasketsLive, fetchBasketDetail } from "@/lib/basket-api";
import type { BasketLiveResponse, BasketDetail } from "@/lib/basket-types";

export function useBasketsLive(base: string) {
  const { data, error, isLoading, mutate } = useSWR<BasketLiveResponse>(
    `baskets-live-${base}`,
    () => fetchBasketsLive(base),
    { refreshInterval: 30000 }
  );
  return {
    data: data ?? { success: false, count: 0, base, baskets: [], timestamp: "" },
    error,
    isLoading,
    mutate,
  };
}

export function useBasketDetail(id: number | null) {
  const { data, error, isLoading, mutate } = useSWR<BasketDetail | null>(
    id ? `basket-detail-${id}` : null,
    () => (id ? fetchBasketDetail(id) : null),
    { refreshInterval: 30000 }
  );
  return { data: data ?? null, error, isLoading, mutate };
}
