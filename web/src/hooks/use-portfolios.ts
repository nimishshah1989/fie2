"use client";

import useSWR from "swr";
import { fetchPortfolios } from "@/lib/portfolio-api";
import type { Portfolio } from "@/lib/portfolio-types";
import { REFRESH_PORTFOLIO } from "@/lib/constants";

export function usePortfolios() {
  const { data, error, isLoading, mutate } = useSWR<Portfolio[]>(
    "portfolios",
    fetchPortfolios,
    { refreshInterval: REFRESH_PORTFOLIO }
  );

  return {
    portfolios: data ?? [],
    error,
    isLoading,
    mutate,
  };
}
