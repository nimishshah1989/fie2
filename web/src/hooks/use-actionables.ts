"use client";
import useSWR from "swr";
import { fetchActionables } from "@/lib/api";
import type { ActionableAlert } from "@/lib/types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useActionables() {
  const { data, error, isLoading, mutate } = useSWR<ActionableAlert[]>(
    "actionables",
    fetchActionables,
    { refreshInterval: REFRESH_MARKET }
  );
  return { actionables: data ?? [], error, isLoading, mutate };
}
