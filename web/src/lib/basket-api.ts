// ============================================================================
// Jhaveri Intelligence Platform — Microbasket API
// ============================================================================

import type {
  BasketSummary,
  BasketDetail,
  BasketLiveResponse,
  CreateBasketPayload,
  UpdateBasketPayload,
  CsvUploadResponse,
} from "@/lib/basket-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchBaskets(): Promise<BasketSummary[]> {
  const res = await fetch(`${API}/api/baskets`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.baskets || [];
}

export async function fetchBasketsLive(base = "NIFTY"): Promise<BasketLiveResponse> {
  const res = await fetch(`${API}/api/baskets/live?base=${base}`);
  if (!res.ok) return { success: false, count: 0, base, baskets: [], timestamp: "" };
  return res.json();
}

export async function fetchBasketDetail(id: number): Promise<BasketDetail | null> {
  const res = await fetch(`${API}/api/baskets/${id}`);
  if (!res.ok) return null;
  return res.json();
}

export async function createBasket(
  payload: CreateBasketPayload
): Promise<{ success: boolean; id?: number; slug?: string; error?: string }> {
  const res = await fetch(`${API}/api/baskets`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function updateBasket(
  id: number,
  payload: UpdateBasketPayload
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/api/baskets/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function archiveBasket(
  id: number
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/api/baskets/${id}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function uploadBasketCSV(
  file: File
): Promise<CsvUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const res = await fetch(`${API}/api/baskets/csv-upload`, {
    method: "POST",
    body: formData,
  });
  return res.json();
}
