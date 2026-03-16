import type { MutualFund, BreadthMetric, SimulationParams, SimulationResult } from "./simulator-types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchFunds(): Promise<MutualFund[]> {
  const res = await fetch(`${API}/api/simulator/funds`);
  if (!res.ok) throw new Error("Failed to fetch funds");
  const data = await res.json();
  return data.funds;
}

export async function fetchMetrics(): Promise<{ short_term: BreadthMetric[]; broad_trend: BreadthMetric[] }> {
  const res = await fetch(`${API}/api/simulator/metrics`);
  if (!res.ok) throw new Error("Failed to fetch metrics");
  const data = await res.json();
  return { short_term: data.short_term, broad_trend: data.broad_trend };
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
