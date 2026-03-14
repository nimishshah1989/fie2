"use client";
import useSWR from "swr";
import { REFRESH_MARKET } from "@/lib/constants";

const API = process.env.NEXT_PUBLIC_API_URL || "";

/** Single sector aggregate from /api/sentiment/sectors */
export interface SectorSentimentItem {
  sector: string;
  sector_key: string;
  avg_score: number;
  zone: string;
  stock_count: number;
  bullish_count: number;
  bearish_count: number;
  neutral_count: number;
}

/** Single stock from /api/sentiment/sector/{key} */
export interface StockSentimentItem {
  ticker: string;
  composite_score: number;
  zone: string;
  above_10ema: boolean;
  above_21ema: boolean;
  above_50ema: boolean;
  above_200ema: boolean;
  golden_cross: boolean;
  rsi_daily: number | null;
  rsi_weekly: number | null;
  macd_bull_cross: boolean;
  hit_52w_high: boolean;
  hit_52w_low: boolean;
  roc_positive: boolean;
  above_prev_month_high: boolean;
}

async function fetchSectorSentiment(): Promise<SectorSentimentItem[]> {
  const res = await fetch(`${API}/api/sentiment/sectors`);
  if (!res.ok) return [];
  const json = await res.json();
  return json.sectors ?? [];
}

async function fetchSectorDetail(key: string): Promise<StockSentimentItem[]> {
  const res = await fetch(`${API}/api/sentiment/sector/${encodeURIComponent(key)}`);
  if (!res.ok) return [];
  const json = await res.json();
  return json.stocks ?? [];
}

export function useSectorSentiment() {
  const { data, error, isLoading, mutate } = useSWR<SectorSentimentItem[]>(
    "sector-sentiment",
    fetchSectorSentiment,
    { refreshInterval: REFRESH_MARKET }
  );
  return { sectors: data ?? [], error, isLoading, mutate };
}

export function useSectorDetail(sectorKey: string | null) {
  const { data, error, isLoading } = useSWR<StockSentimentItem[]>(
    sectorKey ? `sector-detail-${sectorKey}` : null,
    sectorKey ? () => fetchSectorDetail(sectorKey) : null,
    { refreshInterval: REFRESH_MARKET }
  );
  return { stocks: data ?? [], error, isLoading };
}
