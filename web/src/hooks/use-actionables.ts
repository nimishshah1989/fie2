"use client";
import useSWR from "swr";
import { fetchActionables } from "@/lib/api";
import type { ActionableAlert } from "@/lib/types";

export function useActionables() {
  const { data, error, isLoading } = useSWR<ActionableAlert[]>(
    "actionables",
    fetchActionables,
    { refreshInterval: 30000 }
  );
  return { actionables: data ?? [], error, isLoading };
}
