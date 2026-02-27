"use client";
import useSWR from "swr";
import { fetchPerformance } from "@/lib/api";
import type { PerformanceAlert } from "@/lib/types";

export function usePerformance() {
  const { data, error, isLoading } = useSWR<PerformanceAlert[]>(
    "performance",
    fetchPerformance,
    { refreshInterval: 30000 }
  );
  return { performance: data ?? [], error, isLoading };
}
