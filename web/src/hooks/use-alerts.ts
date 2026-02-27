"use client";
import useSWR from "swr";
import { fetchAlerts } from "@/lib/api";
import type { Alert } from "@/lib/types";

export function useAlerts() {
  const { data, error, isLoading, mutate } = useSWR<Alert[]>(
    "alerts",
    () => fetchAlerts(300),
    { refreshInterval: 30000 }
  );
  const alerts = data ?? [];
  const pending = alerts.filter((a) => a.status === "PENDING");
  const approved = alerts.filter((a) => a.status === "APPROVED");
  const denied = alerts.filter((a) => a.status === "DENIED");
  const bullish = alerts.filter((a) => a.signal_direction === "BULLISH").length;
  const bearish = alerts.filter((a) => a.signal_direction === "BEARISH").length;
  return { alerts, pending, approved, denied, bullish, bearish, error, isLoading, mutate };
}
