"use client";
import useSWR from "swr";
import { REFRESH_MARKET } from "@/lib/constants";

const API = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchSentiment() {
  const res = await fetch(`${API}/api/sentiment?include_tickers=true`);
  if (!res.ok) throw new Error(`Sentiment fetch failed: ${res.status}`);
  return res.json();
}

export function useSentiment() {
  const { data, error, isLoading, mutate } = useSWR(
    "sentiment",
    fetchSentiment,
    { refreshInterval: REFRESH_MARKET }
  );
  return { data, error, isLoading, mutate };
}
