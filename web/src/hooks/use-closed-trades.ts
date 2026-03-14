"use client";
import useSWR from "swr";
import { fetchClosedTrades } from "@/lib/api";
import type { ClosedTrade } from "@/lib/types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useClosedTrades() {
  const { data, error, isLoading, mutate } = useSWR<ClosedTrade[]>(
    "closed-trades",
    fetchClosedTrades,
    { refreshInterval: REFRESH_MARKET }
  );
  return { trades: data ?? [], error, isLoading, mutate };
}
