"use client";
import useSWR from "swr";
import { fetchActionables } from "@/lib/api";
import type { ActionableAlert } from "@/lib/types";

export function useActionables() {
  const { data, error, isLoading, mutate } = useSWR<ActionableAlert[]>(
    "actionables",
    fetchActionables,
    { refreshInterval: 900_000 }
  );
  return { actionables: data ?? [], error, isLoading, mutate };
}
