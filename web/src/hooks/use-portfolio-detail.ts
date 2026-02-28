"use client";

import useSWR from "swr";
import {
  fetchPortfolioDetail,
  fetchPortfolioHoldings,
  fetchPortfolioTransactions,
  fetchPortfolioPerformance,
  fetchAllocation,
  fetchNAVHistory,
} from "@/lib/portfolio-api";

export function usePortfolioDetail(id: number | null) {
  const { data: detail, mutate: mutateDetail } = useSWR(
    id ? `portfolio-${id}` : null,
    () => fetchPortfolioDetail(id!),
    { refreshInterval: 60_000 }
  );

  const { data: holdingsData, mutate: mutateHoldings } = useSWR(
    id ? `portfolio-holdings-${id}` : null,
    () => fetchPortfolioHoldings(id!),
    { refreshInterval: 30_000 }
  );

  const { data: transactions, mutate: mutateTransactions } = useSWR(
    id ? `portfolio-txns-${id}` : null,
    () => fetchPortfolioTransactions(id!),
    { refreshInterval: 30_000 }
  );

  const { data: performance } = useSWR(
    id ? `portfolio-perf-${id}` : null,
    () => fetchPortfolioPerformance(id!),
    { refreshInterval: 60_000 }
  );

  const { data: allocation } = useSWR(
    id ? `portfolio-alloc-${id}` : null,
    () => fetchAllocation(id!),
    { refreshInterval: 60_000 }
  );

  return {
    detail,
    holdings: holdingsData?.holdings ?? [],
    totals: holdingsData?.totals ?? null,
    transactions: transactions ?? [],
    performance: performance ?? null,
    allocation: allocation ?? { by_stock: [], by_sector: [] },
    refresh: () => {
      mutateDetail();
      mutateHoldings();
      mutateTransactions();
    },
  };
}

export function useNAVHistory(id: number | null, period: string) {
  const { data } = useSWR(
    id ? `portfolio-nav-${id}-${period}` : null,
    () => fetchNAVHistory(id!, period),
    { refreshInterval: 60_000 }
  );

  return { navHistory: data ?? [] };
}
