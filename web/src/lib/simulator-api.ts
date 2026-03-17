import type { MutualFund, BatchResponse, SimulationParams, SimulationResult } from "./simulator-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchFunds(): Promise<MutualFund[]> {
  const res = await fetch(`${API}/api/simulator/funds`);
  if (!res.ok) throw new Error("Failed to fetch funds");
  const data = await res.json();
  return data.funds;
}

export async function fetchBatch(): Promise<BatchResponse> {
  const res = await fetch(`${API}/api/simulator/batch`);
  if (!res.ok) throw new Error("Failed to fetch batch results");
  return res.json();
}

export async function runSimulation(params: SimulationParams): Promise<SimulationResult> {
  const res = await fetch(`${API}/api/simulator/run`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Simulation failed" }));
    throw new Error(err.detail || "Simulation failed");
  }
  return res.json();
}

export async function fetchBreadthStatus(): Promise<{
  success: boolean;
  total_rows: number;
  metrics: Record<string, { rows: number; first_date?: string; last_date?: string }>;
}> {
  const res = await fetch(`${API}/api/simulator/breadth-status`);
  if (!res.ok) throw new Error("Failed to fetch breadth status");
  return res.json();
}
