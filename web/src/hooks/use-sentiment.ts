"use client";
import useSWR from "swr";

const API = process.env.NEXT_PUBLIC_API_URL || "";

async function fetchSentiment() {
  const res = await fetch(`${API}/api/sentiment`);
  if (!res.ok) throw new Error(`Sentiment fetch failed: ${res.status}`);
  return res.json();
}

export function useSentiment() {
  const { data, error, isLoading, mutate } = useSWR(
    "sentiment",
    fetchSentiment,
    { refreshInterval: 900_000 }   // 15-minute refresh
  );
  return { data, error, isLoading, mutate };
}
