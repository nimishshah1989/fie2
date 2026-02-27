import type {
  Alert,
  ActionRequest,
  PerformanceAlert,
  ActionableAlert,
  IndicesResponse,
  StatusResponse,
} from "@/lib/types";

const API = process.env.NEXT_PUBLIC_API_URL || "";

export async function fetchAlerts(limit = 300): Promise<Alert[]> {
  const res = await fetch(`${API}/api/alerts?limit=${limit}`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.alerts || [];
}

export async function postAction(payload: ActionRequest): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/api/alerts/${payload.alert_id}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function fetchChart(alertId: number): Promise<string> {
  const res = await fetch(`${API}/api/alerts/${alertId}/chart`);
  if (!res.ok) return "";
  const data = await res.json();
  return data.chart_image_b64 || "";
}

export async function fetchPerformance(): Promise<PerformanceAlert[]> {
  const res = await fetch(`${API}/api/performance`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.performance || [];
}

export async function fetchIndicesLive(base = "NIFTY"): Promise<IndicesResponse> {
  const res = await fetch(`${API}/api/indices/live?base=${base}`);
  if (!res.ok) return { success: false, count: 0, base, timestamp: "", indices: [] };
  return res.json();
}

export async function updateAction(
  alertId: number,
  payload: Record<string, unknown>
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/api/alerts/${alertId}/action`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  return res.json();
}

export async function deleteAlert(
  alertId: number
): Promise<{ success: boolean; error?: string }> {
  const res = await fetch(`${API}/api/alerts/${alertId}`, {
    method: "DELETE",
  });
  return res.json();
}

export async function fetchActionables(): Promise<ActionableAlert[]> {
  const res = await fetch(`${API}/api/actionables`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.actionables || [];
}

export async function fetchStatus(): Promise<StatusResponse> {
  const res = await fetch(`${API}/api/status`);
  if (!res.ok) return { analysis_enabled: false, version: "3.0" };
  return res.json();
}
