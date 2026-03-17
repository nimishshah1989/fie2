import type { GlobalMarketsResponse } from "@/lib/global-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchGlobalMarkets(): Promise<GlobalMarketsResponse> {
  const res = await fetch(`${API}/api/global-markets/live`);
  if (!res.ok) return { success: false, markets: [], timestamp: "" };
  return res.json();
}
