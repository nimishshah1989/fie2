"use client";
import useSWR from "swr";
import { fetchStatus } from "@/lib/api";
import type { StatusResponse } from "@/lib/types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useStatus() {
  const { data } = useSWR<StatusResponse>("status", fetchStatus, { refreshInterval: REFRESH_MARKET });
  return { analysisEnabled: data?.analysis_enabled ?? true };
}
