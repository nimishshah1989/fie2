import type {
  GlobalIndicesResponse,
  GlobalSectorsResponse,
  GlobalStocksResponse,
} from "./global-pulse-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchGlobalIndices(base = "NIFTY50"): Promise<GlobalIndicesResponse> {
  const res = await fetch(`${API}/api/global-pulse/indices?base=${base}`);
  if (!res.ok) throw new Error(`Failed to fetch global indices: ${res.status}`);
  return res.json();
}

export async function fetchGlobalSectors(market: string, base = "NIFTY50"): Promise<GlobalSectorsResponse> {
  const res = await fetch(`${API}/api/global-pulse/sectors?market=${market}&base=${base}`);
  if (!res.ok) throw new Error(`Failed to fetch sectors: ${res.status}`);
  return res.json();
}

export async function fetchGlobalStocks(sector: string): Promise<GlobalStocksResponse> {
  const res = await fetch(`${API}/api/global-pulse/stocks?sector=${sector}`);
  if (!res.ok) throw new Error(`Failed to fetch stocks: ${res.status}`);
  return res.json();
}
