"use client";

import useSWR from "swr";
import { fetchPortfolios } from "@/lib/portfolio-api";
import type { Portfolio } from "@/lib/portfolio-types";

export function usePortfolios() {
  const { data, error, isLoading, mutate } = useSWR<Portfolio[]>(
    "portfolios",
    fetchPortfolios,
    { refreshInterval: 30_000 }
  );

  return {
    portfolios: data ?? [],
    error,
    isLoading,
    mutate,
  };
}
