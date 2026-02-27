"use client";
import useSWR from "swr";
import { fetchIndicesLive } from "@/lib/api";
import type { IndicesResponse } from "@/lib/types";

export function useIndices(base: string) {
  const { data, error, isLoading, mutate } = useSWR<IndicesResponse>(
    `indices-${base}`,
    () => fetchIndicesLive(base),
    { refreshInterval: 30000 }
  );
  return { data: data ?? { success: false, count: 0, base, timestamp: "", indices: [] }, error, isLoading, mutate };
}
