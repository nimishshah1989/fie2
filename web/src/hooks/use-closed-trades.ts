"use client";
import useSWR from "swr";
import { fetchClosedTrades } from "@/lib/api";
import type { ClosedTrade } from "@/lib/types";

export function useClosedTrades() {
  const { data, error, isLoading, mutate } = useSWR<ClosedTrade[]>(
    "closed-trades",
    fetchClosedTrades,
    { refreshInterval: 900_000 }
  );
  return { trades: data ?? [], error, isLoading, mutate };
}
