"use client";
import { useMemo } from "react";
import useSWR from "swr";
import { fetchActioned } from "@/lib/api";
import type { ActionedResponse } from "@/lib/types";
import { REFRESH_MARKET } from "@/lib/constants";

export function useActioned() {
  const { data, error, isLoading, mutate } = useSWR<ActionedResponse>(
    "actioned",
    fetchActioned,
    { refreshInterval: REFRESH_MARKET }
  );

  const alerts = data?.alerts ?? [];

  const active = useMemo(
    () => alerts.filter((a) => !a.is_closed && !a.target_hit && !a.sl_hit),
    [alerts]
  );

  const triggered = useMemo(
    () => alerts.filter((a) => !a.is_closed && (a.target_hit || a.sl_hit)),
    [alerts]
  );

  const closed = useMemo(
    () => alerts.filter((a) => a.is_closed),
    [alerts]
  );

  return {
    alerts,
    active,
    triggered,
    closed,
    counts: data?.counts ?? { total: 0, active: 0, triggered: 0, closed: 0 },
    error,
    isLoading,
    mutate,
  };
}
