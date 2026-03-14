"use client";

import useSWR from "swr";
import { REFRESH_MARKET } from "@/lib/constants";

const API = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchHistory() {
  const res = await fetch(`${API}/api/sentiment/history?weeks=20`);
  if (!res.ok) throw new Error(`Sentiment history fetch failed: ${res.status}`);
  return res.json();
}

export function useSentimentHistory() {
  const { data, error, isLoading } = useSWR("sentiment-history", fetchHistory, {
    refreshInterval: REFRESH_MARKET,
  });
  return { data, error, isLoading };
}
