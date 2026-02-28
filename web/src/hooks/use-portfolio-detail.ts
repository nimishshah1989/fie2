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
  // Detail is lightweight DB call — can refresh frequently
  const { data: detail, mutate: mutateDetail } = useSWR(
    id ? `portfolio-${id}` : null,
    () => fetchPortfolioDetail(id!),
    { refreshInterval: 120_000 }
  );

  // Holdings triggers Yahoo Finance calls — refresh every 2 min (cache on backend is 60s)
  const { data: holdingsData, mutate: mutateHoldings } = useSWR(
    id ? `portfolio-holdings-${id}` : null,
    () => fetchPortfolioHoldings(id!),
    { refreshInterval: 120_000 }
  );

  // Transactions are DB-only, rarely change
  const { data: transactions, mutate: mutateTransactions } = useSWR(
    id ? `portfolio-txns-${id}` : null,
    () => fetchPortfolioTransactions(id!),
    { refreshInterval: 120_000 }
  );

  // Performance also triggers Yahoo calls — 2 min refresh (backend cache will serve)
  const { data: performance } = useSWR(
    id ? `portfolio-perf-${id}` : null,
    () => fetchPortfolioPerformance(id!),
    { refreshInterval: 120_000 }
  );

  // Allocation also uses live prices — 2 min refresh
  const { data: allocation } = useSWR(
    id ? `portfolio-alloc-${id}` : null,
    () => fetchAllocation(id!),
    { refreshInterval: 120_000 }
  );

  return {
    detail,
    holdings: holdingsData?.holdings ?? [],
    totals: holdingsData?.totals ?? null,
    pricesAsOf: holdingsData?.prices_as_of ?? null,
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
  // NAV history is DB-only, no live prices — but can be large dataset
  const { data } = useSWR(
    id ? `portfolio-nav-${id}-${period}` : null,
    () => fetchNAVHistory(id!, period),
    { refreshInterval: 300_000 }  // 5 min — NAV data doesn't change intraday
  );

  return { navHistory: data ?? [] };
}
