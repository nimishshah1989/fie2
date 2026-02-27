"use client";
import useSWR from "swr";
import { fetchStatus } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";

export function useStatus() {
  const { data } = useSWR<StatusResponse>("status", fetchStatus, { refreshInterval: 60000 });
  return { analysisEnabled: data?.analysis_enabled ?? true };
}
