"use client";

import useSWR from "swr";
import {
  fetchPmsNav,
  fetchPmsMetrics,
  fetchPmsDrawdowns,
  fetchPmsSummary,
} from "@/lib/pms-api";
import { REFRESH_PORTFOLIO } from "@/lib/constants";

export function usePmsDetail(portfolioId: number | null) {
  const { data: summary, isLoading: summaryLoading, mutate: mutateSummary } = useSWR(
    portfolioId ? `pms-summary-${portfolioId}` : null,
    () => fetchPmsSummary(portfolioId!),
    { refreshInterval: REFRESH_PORTFOLIO }
  );

  const { data: metricsData, mutate: mutateMetrics } = useSWR(
    portfolioId ? `pms-metrics-${portfolioId}` : null,
    () => fetchPmsMetrics(portfolioId!),
    { refreshInterval: REFRESH_PORTFOLIO }
  );

  const { data: drawdowns, mutate: mutateDrawdowns } = useSWR(
    portfolioId ? `pms-drawdowns-${portfolioId}` : null,
    () => fetchPmsDrawdowns(portfolioId!),
    { refreshInterval: REFRESH_PORTFOLIO }
  );

  return {
    summary: summary ?? null,
    summaryLoading,
    metrics: metricsData?.metrics ?? [],
    metricsAsOf: metricsData?.as_of_date ?? null,
    drawdowns: drawdowns ?? [],
    refresh: () => {
      mutateSummary();
      mutateMetrics();
      mutateDrawdowns();
    },
  };
}

export function usePmsNav(portfolioId: number | null, period: string = "all") {
  const { data } = useSWR(
    portfolioId ? `pms-nav-${portfolioId}-${period}` : null,
    () => fetchPmsNav(portfolioId!, period),
    { refreshInterval: REFRESH_PORTFOLIO }
  );

  return { navHistory: data ?? [] };
}
