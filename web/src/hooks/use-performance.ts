"use client";
import useSWR from "swr";
import { fetchPerformance } from "@/lib/api";
import type { PerformanceAlert } from "@/lib/types";
import { REFRESH_MARKET } from "@/lib/constants";

export function usePerformance() {
  const { data, error, isLoading } = useSWR<PerformanceAlert[]>(
    "performance",
    fetchPerformance,
    { refreshInterval: REFRESH_MARKET }
  );
  return { performance: data ?? [], error, isLoading };
}
